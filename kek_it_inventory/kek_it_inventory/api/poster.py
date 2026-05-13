import frappe
import requests
import json
from frappe import _
from kek_it_inventory.kek_it_inventory.api.ledger import update_ledger

def post_transaction(docname):
	"""
	Posts a KEK Inventory Transaction to SINSW Gateway with real credentials.
	"""
	doc = frappe.get_doc("KEK Inventory Transaction", docname)
	
	# 1. Fetch Company Profile
	profile = frappe.get_doc("KEK Company Profile", doc.company_profile)
	
	# 2. Fetch Active Credentials
	cred_name = frappe.db.get_value("KEK API Credential", 
		{"company_profile": profile.name, "active": 1}, "name")
	
	if not cred_name:
		frappe.log_error(f"No active API Credentials found for {profile.name}", "KEK Integration Error")
		doc.status = "FAILED"
		doc.save()
		return

	cred = frappe.get_doc("KEK API Credential", cred_name)
	
	# 3. Decrypt Keys
	insw_key = cred.get_password("x_insw_key")
	unique_key = cred.get_password("x_unique_key")

	# 4. Prepare Payload (Sharpened for SINSW KEK API)
	payload = {
		"npwp": profile.npwp,
		"nib": profile.nib,
		"tglTransaksi": str(doc.transaction_date),
		"kodeKegiatan": doc.transaction_type, # e.g., 30 or 31
		"referensiInternal": doc.erpnext_reference_name,
		"details": []
	}
	
	for item in doc.items:
		payload["details"].append({
			"kodeBarang": item.customs_item_code,
			"jumlah": item.qty,
			"kodeSatuan": item.uom_code,
			"kodeAsalBarang": item.origin_type or "TLDDP",
			"kodeTujuanPengiriman": item.business_flow_type or "PROCESSING"
		})
	
	# 5. Execute Request
	headers = {
		"Content-Type": "application/json",
		"X-INSW-Key": insw_key,
		"X-Unique-Key": unique_key
	}
	
	endpoint = f"{cred.base_url.rstrip('/')}/transaksi/v1/kirim"
	
	try:
		# Use timeout to prevent worker hang
		response = requests.post(endpoint, data=json.dumps(payload), headers=headers, timeout=30)
		
		# Log Request for debugging (Optional, but useful during implementation)
		# frappe.log_error(f"Payload: {json.dumps(payload)}", "KEK API Request")

		if response.status_code in [200, 201]:
			res_data = response.json()
			doc.status = "SENT"
			doc.insw_transaksi_id = res_data.get("idTransaksi") or res_data.get("id_transaksi")
			doc.save()
			
			# Trigger Ledger Update
			update_ledger(doc.name)
			
			# Reset failure count
			if cred.failure_count > 0:
				cred.failure_count = 0
				cred.save(ignore_permissions=True)
				
		else:
			doc.status = "FAILED"
			error_msg = response.text
			doc.add_comment("Comment", f"❌ API Error ({response.status_code}): {error_msg[:200]}")
			doc.save()
			
			# Track failure on credential
			cred.failure_count += 1
			cred.save(ignore_permissions=True)

	except Exception as e:
		doc.status = "FAILED"
		doc.add_comment("Comment", f"⚠️ Connection Error: {str(e)}")
		doc.save()
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
