import frappe

def create_kek_transaction(doc, method=None):
	"""
	Automatically creates a KEK Inventory Transaction from ERPNext documents
	with sharpened item mapping.
	"""
	# Map Transaction Type
	txn_type = None
	if doc.doctype == "Purchase Receipt":
		txn_type = "30"
	elif doc.doctype == "Delivery Note":
		txn_type = "31"
	
	if not txn_type:
		return

	# Check if company profile exists
	profile = frappe.db.get_value("KEK Company Profile", {"erpnext_company": doc.company}, "name")
	if not profile:
		return

	# Create KEK Transaction
	kek_txn = frappe.get_doc({
		"doctype": "KEK Inventory Transaction",
		"company_profile": profile,
		"transaction_date": doc.posting_date,
		"transaction_type": txn_type,
		"erpnext_reference_doctype": doc.doctype,
		"erpnext_reference_name": doc.name,
		"items": []
	})

	for item in doc.items:
		# Sharp Mapping Logic
		mapping = frappe.db.get_value("KEK Item Mapping", 
			{"erpnext_item": item.item_code}, 
			["customs_item_code", "customs_item_name", "hs_code"], 
			as_dict=1
		)

		if mapping:
			customs_code = mapping.customs_item_code
			customs_name = mapping.customs_item_name or item.item_name
			hs_code = mapping.hs_code
		else:
			# Fallback to ERPNext defaults
			customs_code = item.item_code
			customs_name = item.item_name
			hs_code = None

		kek_txn.append("items", {
			"customs_item_code": customs_code,
			"qty": item.qty,
			"uom_code": item.uom,
			"origin_type": "TLDDP", 
			"business_flow_type": "PROCESSING"
		})

	kek_txn.insert(ignore_permissions=True)
	frappe.msgprint(f"KEK Transaction {kek_txn.name} created automatically.")
