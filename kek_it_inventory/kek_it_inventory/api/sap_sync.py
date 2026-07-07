import frappe
import json
import traceback
import requests
from frappe.utils import now_datetime

def normalize_uom(sap_uom):
	if not sap_uom:
		return sap_uom

	sap_uom = sap_uom.strip()

	# 1. Direct match in UOM DocType
	if frappe.db.exists("UOM", sap_uom):
		return sap_uom

	# 2. Case-insensitive or fuzzy match in UOM DocType
	uom_name = frappe.db.get_value("UOM", {"name": ["like", sap_uom]}, "name")
	if uom_name:
		return uom_name

	# 3. Map common SAP UOM codes
	mapping = {
		"EA": "Unit",
		"PC": "Unit",
		"PCS": "Unit",
		"BOX": "Box",
		"KG": "Kg",
		"L": "Litre",
		"M": "Meter"
	}
	mapped = mapping.get(sap_uom.upper())
	if mapped and frappe.db.exists("UOM", mapped):
		return mapped

	# 4. Fallback to 'Unit' if it exists in UOM DocType
	if frappe.db.exists("UOM", "Unit"):
		return "Unit"

	return sap_uom


@frappe.whitelist()
def receive_sap_document():
	"""
	Whitelisted POST endpoint for SAP HANA to push PO/SO data.
	"""
	if frappe.request.method != "POST":
		frappe.throw("Only POST method is allowed", frappe.PermissionError)

	try:
		# Parse payload
		if isinstance(frappe.request.data, bytes):
			raw_payload = frappe.request.data.decode("utf-8")
		else:
			raw_payload = frappe.request.data

		payload = json.loads(raw_payload)
	except Exception as e:
		frappe.throw(f"Invalid JSON payload: {str(e)}", frappe.ValidationError)

	doc_num = payload.get("PurchaseOrder") or payload.get("SalesOrder")
	doc_type = "Purchase Order" if payload.get("PurchaseOrder") else "Sales Order"

	if not doc_num:
		frappe.throw("Missing document identifier (PurchaseOrder or SalesOrder)", frappe.ValidationError)

	# Create SAP Integration Log entry
	log = frappe.get_doc({
		"doctype": "SAP Integration Log",
		"sap_document_number": doc_num,
		"document_type": doc_type,
		"status": "Pending",
		"sap_payload": raw_payload,
		"sync_timestamp": frappe.utils.now_datetime()
	})
	log.insert(ignore_permissions=True)
	frappe.db.commit()

	# Enqueue processing job to run asynchronously
	frappe.enqueue(
		method="kek_it_inventory.kek_it_inventory.api.sap_sync.process_sap_document_async",
		queue="default",
		job_name=f"SAP-Sync-{doc_num}",
		log_name=log.name
	)

	return {
		"status": "Queued",
		"message": "Document received and queued for processing",
		"log_name": log.name
	}

@frappe.whitelist()
def process_sap_document_async(log_name):
	"""
	Asynchronously processes an SAP Integration Log record.
	"""
	log = frappe.get_doc("SAP Integration Log", log_name)
	log.status = "Processing"
	log.save(ignore_permissions=True)
	frappe.db.commit()

	try:
		payload = json.loads(log.sap_payload)
		
		if log.document_type == "Purchase Order":
			create_purchase_order(payload, log)
		else:
			raise NotImplementedError("Sales Order synchronization is not yet implemented")

		log.status = "Success"
		log.error_trace = None
		log.save(ignore_permissions=True)
	except Exception as e:
		frappe.db.rollback()
		log.status = "Failed"
		log.error_trace = f"{str(e)}\n\n{traceback.format_exc()}"
		log.save(ignore_permissions=True)
	finally:
		frappe.db.commit()

def create_purchase_order(sap_po, log):
	po_number = sap_po.get("PurchaseOrder")

	# Idempotency check: see if PO already exists
	existing_po = frappe.db.get_value("Purchase Order", {"custom_sap_po_number": po_number}, "name")
	if existing_po:
		log.erpnext_reference = existing_po
		return

	# Validate Supplier
	supplier = sap_po.get("Supplier")
	if not frappe.db.exists("Supplier", supplier):
		raise frappe.ValidationError(f"Supplier {supplier} not found in ERPNext")

	# Validate Company
	company = sap_po.get("CompanyCode")
	if not frappe.db.exists("Company", company):
		raise frappe.ValidationError(f"Company {company} not found in ERPNext")

	# Process items
	items = []
	raw_items = sap_po.get("to_PurchaseOrderItem", {}).get("results", [])
	
	for idx, it in enumerate(raw_items):
		item_code = it.get("Material")
		if not frappe.db.exists("Item", item_code):
			raise frappe.ValidationError(f"Item {item_code} at index {idx} not found in ERPNext")

		warehouse = it.get("Plant")
		if not frappe.db.exists("Warehouse", warehouse):
			raise frappe.ValidationError(f"Warehouse {warehouse} at index {idx} not found in ERPNext")

		items.append({
			"item_code": item_code,
			"qty": float(it.get("OrderQuantity") or 0.0),
			"uom": normalize_uom(it.get("PurchaseOrderQuantityUnit")),
			"rate": float(it.get("NetPriceAmount") or 0.0),
			"warehouse": warehouse,
			"description": it.get("PurchaseOrderItemText") or "",
			"schedule_date": sap_po.get("CreationDate")[:10] if sap_po.get("CreationDate") else frappe.utils.today()
		})

	if not items:
		raise frappe.ValidationError("No items found in SAP Purchase Order payload")

	# Create ERPNext Purchase Order
	po = frappe.get_doc({
		"doctype": "Purchase Order",
		"supplier": supplier,
		"company": company,
		"currency": sap_po.get("DocumentCurrency") or "IDR",
		"transaction_date": sap_po.get("CreationDate")[:10] if sap_po.get("CreationDate") else frappe.utils.today(),
		"custom_sap_po_number": po_number,
		"items": items
	})
	po.insert(ignore_permissions=True)
	po.submit()

	log.erpnext_reference = po.name

@frappe.whitelist()
def process_sap_xls_chunked(job_name):
	"""
	XLS Chunked Background Processor (Hybrid Method).
	Driven by the 'SAP PO Import Job' DocType.
	"""
	import pandas as pd
	job = frappe.get_doc("SAP PO Import Job", job_name)
	if job.status == "Completed":
		return

	job.status = "Processing"
	job.save(ignore_permissions=True)
	frappe.db.commit()

	try:
		file_path = frappe.get_site_path(job.file_url.lstrip("/"))
		df = pd.read_excel(file_path)

		# Group all POs (preserve original file order)
		po_groups = list(df.groupby("po_number", sort=False))

		# Set total_rows once from the full file
		if not job.total_rows:
			job.total_rows = len(po_groups)
			job.save(ignore_permissions=True)
			frappe.db.commit()

		# BUG FIX: Index-based resume — NOT lexicographic string comparison
		if job.last_po_number:
			keys = [str(k) for k, _ in po_groups]
			if job.last_po_number in keys:
				start_idx = keys.index(job.last_po_number) + 1
				po_groups = po_groups[start_idx:]

		CHUNK_SIZE = 100
		chunk = po_groups[:CHUNK_SIZE]
		remaining = po_groups[CHUNK_SIZE:]

		for po_number, group in chunk:
			try:
				# Map XLS columns to SAP-shaped dict so create_purchase_order can process
				first_row = group.iloc[0]
				sap_po = {
					"PurchaseOrder": str(po_number),
					"Supplier": str(first_row["supplier"]),
					"CompanyCode": str(first_row["company"]),
					"DocumentCurrency": str(first_row.get("currency", "IDR")),
					"CreationDate": str(first_row.get("transaction_date", frappe.utils.today())),
					"to_PurchaseOrderItem": {"results": [
						{
							"Material": str(row["item_code"]),
							"OrderQuantity": float(row["qty"]),
							"PurchaseOrderQuantityUnit": str(row["uom"]),
							"NetPriceAmount": float(row["rate"]),
							"Plant": str(row["warehouse"]),
							"PurchaseOrderItemText": str(row.get("description", ""))
						}
						for _, row in group.iterrows()
					]}
				}

				# Create SAP Integration Log entry for audit trail
				log_entry = frappe.get_doc({
					"doctype": "SAP Integration Log",
					"sap_document_number": str(po_number),
					"document_type": "Purchase Order",
					"status": "Pending",
					"sap_payload": json.dumps(sap_po),
					"sync_timestamp": now_datetime()
				})
				log_entry.insert(ignore_permissions=True)

				# Reuse the same create_purchase_order shared with push & pull paths
				create_purchase_order(sap_po, log_entry)
				log_entry.status = "Success"
				log_entry.save(ignore_permissions=True)

				job.processed_rows += 1
				job.last_po_number = str(po_number)

			except Exception as row_error:
				frappe.db.rollback()  # Release dirty transaction before next row
				error_msg = f"\nPO {po_number}: {str(row_error)}"
				job.error_log = (job.error_log or "") + error_msg
				frappe.log_error(f"SAP XLS Import Row Error: {po_number}", str(row_error))

		job.save(ignore_permissions=True)
		frappe.db.commit()

		# BUG FIX: Re-enqueue based on remaining list, not `total > CHUNK_SIZE`
		if remaining:
			frappe.enqueue(
				method="kek_it_inventory.kek_it_inventory.api.sap_sync.process_sap_xls_chunked",
				queue="long",
				job_name=job_name,
				timeout=3600
			)
			return  # Hand off to next worker

		job.status = "Completed"
		job.save(ignore_permissions=True)
		frappe.db.commit()

	except Exception as e:
		frappe.db.rollback()
		job.status = "Failed"
		job.error_log = (job.error_log or "") + f"\nJob-level Failure: {str(e)}\n{traceback.format_exc()}"
		job.save(ignore_permissions=True)
		frappe.db.commit()


@frappe.whitelist()
def run_po_sync():
	"""
	Scheduled OData pull: fetches POs from SAP S/4HANA and creates them in ERPNext.
	Registered in hooks.py scheduler_events (e.g. every 15 minutes).
	This is the PULL counterpart to receive_sap_document (PUSH).
	"""
	settings = frappe.get_doc("SAP Sync Settings")
	last_sync = settings.last_sync_timestamp or "2026-01-01T00:00:00"

	sap_base = settings.sap_base_url
	auth = (settings.sap_user, settings.get_password("sap_password"))

	url = f"{sap_base}/A_PurchaseOrder"
	params = {
		"$expand": "to_PurchaseOrderItem",
		"$filter": f"CreationDate ge datetime'{last_sync}'",
		"$top": 5000
	}

	all_pos = []
	while url:
		try:
			r = requests.get(
				url,
				params=params,
				headers={"Accept": "application/json"},
				auth=auth,
				timeout=30
			)
			r.raise_for_status()
			data = r.json()
			all_pos.extend(data["d"]["results"])
			url = data["d"].get("__next")
			params = None  # Only used on first page request
		except Exception as e:
			frappe.log_error(f"SAP OData Fetch Error: {str(e)}", "SAP PO Sync")
			break

	success_count = 0
	skip_count = 0
	error_count = 0

	for sap_po in all_pos:
		try:
			# Reuse the same create_purchase_order used by push & XLS paths
			po_number = sap_po.get("PurchaseOrder")
			existing = frappe.db.get_value("Purchase Order", {"custom_sap_po_number": po_number}, "name")
			if existing:
				skip_count += 1
				continue

			# Use a throwaway log object to satisfy create_purchase_order signature
			log = frappe._dict({"erpnext_reference": None})
			create_purchase_order(sap_po, log)
			success_count += 1

		except Exception as e:
			frappe.db.rollback()
			error_count += 1
			frappe.log_error(
				f"PO {sap_po.get('PurchaseOrder', 'UNKNOWN')}: {str(e)}\n{traceback.format_exc()}",
				"SAP PO Sync"
			)

	settings.last_sync_timestamp = now_datetime()
	settings.save()
	frappe.db.commit()

	return {
		"total": len(all_pos),
		"created": success_count,
		"skipped": skip_count,
		"errors": error_count
	}


