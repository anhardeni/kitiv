import frappe

def create_kek_transaction(doc, method=None):
	"""
	Automatically creates a KEK Inventory Transaction from ERPNext documents
	with sharpened item mapping.
	"""
	# Map Transaction Type
	txn_type = None
	if doc.doctype in ["Purchase Receipt", "Purchase Order", "Subcontracting Order"]:
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
		"transaction_date": doc.get("posting_date") or doc.get("transaction_date"),
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

	# Populate customs docs if present
	if doc.get("custom_bc_registration_no"):
		doc_type_raw = doc.get("custom_bc_document_type") or "Lainnya"
		
		# Map ERPNext Select value to SINSW numeric code
		bc_doc_mapping = {
			"BC23": "0407611",   # PPKEK Pemasukan LDP
			"PPKEK Pemasukan LDP (BC23)": "0407611",
			"BC40": "0407613",   # PPKEK Pemasukan TLDDP
			"PPKEK Pemasukan TLDDP (BC40)": "0407613",
			"BC16": "0407613",   # PPKEK Pemasukan TLDDP (fallback)
			"PPKEK Pemasukan TLDDP (BC16)": "0407613",
			"BC262": "0407614",  # PPKEK Pemasukan Kembali ex-Subkon (formerly Dokumen Pabean General)
			"PPKEK Pemasukan Kembali ex-Subkon (BC262)": "0407614",
			"BC30": "0407631",   # PPKEK Pengeluaran LDP (Ekspor)
			"PPKEK Pengeluaran LDP (BC30)": "0407631",
			"BC25": "0407632",   # PPKEK Pengeluaran ke TLDDP
			"PPKEK Pengeluaran TLDDP (BC25)": "0407632",
			"BC27": "0407621",   # PPKEK Pemasukan ex-Kawasan Berikat/TPB
			"PPKEK Pemasukan ex-Kawasan Berikat/TPB (BC27)": "0407621",
			"BC261": "0407633",  # PPKEK Pengeluaran Sementara (Subkon)
			"PPKEK Pengeluaran Sementara Subkon (BC261)": "0407633",
			"Lainnya": "0407000"
		}
		doc_code = bc_doc_mapping.get(doc_type_raw, "0407000")
		
		# Format date to YYYY-MM-DD for database storage
		doc_date = doc.get("custom_bc_registration_date") or doc.get("posting_date") or doc.get("transaction_date")
		
		for item_row in kek_txn.items:
			frappe.get_doc({
				"doctype": "KEK Item Customs Doc",
				"parent": item_row.name,
				"parenttype": "KEK Inventory Transaction Item",
				"parentfield": "customs_docs",
				"customs_doc_code": doc_code,
				"customs_doc_number": doc.custom_bc_registration_no,
				"customs_doc_date": doc_date
			}).insert(ignore_permissions=True)

	# Update fields in parent document if they exist
	if doc.doctype in ["Purchase Receipt", "Delivery Note", "Purchase Order", "Subcontracting Order"]:
		meta = frappe.get_meta(doc.doctype)
		update_dict = {}
		if meta.has_field("kek_status"):
			if doc.get("bypass_kek_validation"):
				update_dict["kek_status"] = "BYPASSED"
			else:
				update_dict["kek_status"] = "PENDING" if doc.doctype in ["Purchase Order", "Subcontracting Order"] else "QUEUED"
		if meta.has_field("kek_transaction"):
			update_dict["kek_transaction"] = kek_txn.name
		if update_dict:
			frappe.db.set_value(doc.doctype, doc.name, update_dict, update_modified=False)

	frappe.msgprint(f"KEK Transaction {kek_txn.name} created automatically.")

