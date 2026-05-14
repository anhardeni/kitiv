import frappe
import requests
import json
from frappe import _
from kek_it_inventory.kek_it_inventory.api.ledger import update_ledger

def get_unique_key(cred):
	"""
	Retrieves the dynamic X-Unique-Key from SINSW.
	"""
	endpoint = f"{cred.base_url.rstrip('/')}/api/getUniqueKey" # Adjust based on real API path
	insw_key = cred.get_password("x_insw_key")
	
	try:
		response = requests.get(endpoint, headers={"X-INSW-Key": insw_key}, timeout=10)
		if response.status_code == 200:
			data = response.json()
			return data.get("uniqueKey") or data.get("unique_key")
	except Exception as e:
		error_title = f"Failed to fetch KEK Unique Key: {str(e)}"
		frappe.log_error(error_title[:140], "KEK API Error")
	
	return None

def post_transaction(docname):
	"""
	Posts a KEK Inventory Transaction to SINSW Gateway following KEK PDF standards.
	"""
	doc = frappe.get_doc("KEK Inventory Transaction", docname)
	profile = frappe.get_doc("KEK Company Profile", doc.company_profile)
	
	cred_name = frappe.db.get_value("KEK API Credential", 
		{"company_profile": profile.name, "active": 1}, "name")
	
	if not cred_name:
		frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
		doc.add_comment("Comment", "❌ No active API Credentials found.")
		return

	cred = frappe.get_doc("KEK API Credential", cred_name)
	insw_key = cred.get_password("x_insw_key")
	unique_key = get_unique_key(cred) or cred.get_password("x_unique_key")

	# 1. Build Nested Payload (Strictly following KEK PDF Structure)
	# Structure: data[] -> kdKegiatan, dokumenKegiatan[] -> barangTransaksi[] -> dokumen[]
	payload = {
		"data": [
			{
				"nomorAju": doc.name,
				"npwp": profile.npwp,
				"nib": profile.nib,
				"kdKegiatan": doc.transaction_type, 
				"dokumenKegiatan": [
					{
						"nomorDokKegiatan": doc.erpnext_reference_name or doc.name,
						"tanggalKegiatan": frappe.utils.formatdate(doc.transaction_date, "dd-mm-yyyy"),
						"namaEntitas": profile.company_name,
						"barangTransaksi": []
					}
				]
			}
		]
	}
	
	for item in doc.items:
		barang = {
			"kdKategoriBarang": item.category_code or "1",
			"kdBarang": item.customs_item_code,
			"uraianBarang": item.item_name_customs or item.customs_item_code,
			"jumlah": item.qty,
			"kdSatuan": item.uom_code,
			"nilai": item.amount_idr or 0,
			"dokumen": [] 
		}
		
		# Add nested Customs Documents from child table
		customs_docs = item.get("customs_docs")
		if not customs_docs:
			customs_docs = frappe.get_all("KEK Item Customs Doc", filters={"parent": item.name}, fields=["*"])
		
		for doc_ref in customs_docs:
			is_dict = isinstance(doc_ref, dict)
			barang["dokumen"].append({
				"kodeDokumen": doc_ref.get("customs_doc_code") if is_dict else doc_ref.customs_doc_code,
				"nomorDokumen": doc_ref.get("customs_doc_number") if is_dict else doc_ref.customs_doc_number,
				"tanggalDokumen": frappe.utils.formatdate(doc_ref.get("customs_doc_date") if is_dict else doc_ref.customs_doc_date, "dd-mm-yyyy")
			})
		
		payload["data"][0]["dokumenKegiatan"][0]["barangTransaksi"].append(barang)

	# 2. Execute Request
	headers = {
		"Content-Type": "application/json",
		"X-INSW-Key": insw_key,
		"X-Unique-Key": unique_key
	}
	
	# Determine endpoint based on activity (Mapping from doc.transaction_type)
	# Default common endpoint for transactions
	endpoint = f"{cred.base_url.rstrip('/')}/api/inventory/transaksi"
	
	try:
		request_payload_json = json.dumps(payload, indent=4)
		frappe.db.set_value("KEK Inventory Transaction", doc.name, "request_payload", request_payload_json)
		
		response = requests.post(endpoint, data=json.dumps(payload), headers=headers, timeout=30)
		
		frappe.db.set_value("KEK Inventory Transaction", doc.name, "response_payload", response.text)

		if response.status_code in [200, 201]:
			res_data = response.json()
			
			# PDF Standard: status=true and code="01" indicates success
			if res_data.get("status") is True or res_data.get("code") == "01":
				# Extract dynamic ID if provided by SINSW
				result_data = res_data.get("data", {}).get("resultDataTransaksi", [{}])[0]
				insw_id = result_data.get("idTransaksi")
				
				frappe.db.set_value("KEK Inventory Transaction", doc.name, {
					"status": "SENT",
					"insw_transaksi_id": insw_id
				})
				
				# Trigger Ledger Update only on successful report
				update_ledger(doc.name)
				
				# Reset failure count
				if cred.failure_count > 0:
					frappe.db.set_value("KEK API Credential", cred.name, "failure_count", 0)
			else:
				frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
				msg = res_data.get("message") or "Unknown SINSW error"
				doc.add_comment("Comment", f"❌ SINSW Rejection: {msg}")
				
		else:
			frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
			error_msg = response.text
			doc.add_comment("Comment", f"❌ API Error ({response.status_code}): {error_msg[:200]}")
			
			# Track failure on credential
			frappe.db.set_value("KEK API Credential", cred.name, "failure_count", cred.failure_count + 1)

	except Exception as e:
		frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
		doc.add_comment("Comment", f"⚠️ Connection Error: {str(e)}")
		frappe.log_error(frappe.get_traceback(), "KEK Integration Connection Error")

def process_queue(sync=False):
	"""
	Finds all QUEUED transactions and attempts to post them.
	"""
	queued_txns = frappe.get_all("KEK Inventory Transaction", 
		filters={"status": "QUEUED"},
		fields=["name"]
	)
	
	for txn in queued_txns:
		if sync:
			post_transaction(txn.name)
		else:
			frappe.enqueue(
				"kek_it_inventory.kek_it_inventory.api.poster.post_transaction",
				docname=txn.name,
				queue="long",
				timeout=300
			)
