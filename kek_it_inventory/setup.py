import frappe
import json

def seed_master_data():
	"""Seed master reference data for KEK IT Inventory"""
	
	# 1. KEK Ref Transaction Type
	transaction_types = [
		{"code": "30", "description": "Incoming Goods"},
		{"code": "31", "description": "Outgoing Goods"},
		{"code": "32", "description": "Stock Opname Goods"},
		{"code": "33", "description": "Adjustment Goods"}
	]
	seed_doctype("KEK Ref Transaction Type", transaction_types)

	# 2. KEK Ref Item Category
	item_categories = [
		{"code": "1", "description": "Bahan Baku"},
		{"code": "2", "description": "Bahan Penolong"},
		{"code": "3", "description": "Bahan Habis Pakai"},
		{"code": "4", "description": "Barang Dagangan"},
		{"code": "5", "description": "Mesin dan Peralatan"},
		{"code": "6", "description": "Barang dalam Proses"},
		{"code": "7", "description": "Barang Jadi"},
		{"code": "8", "description": "Barang Reject & Scrap"}
	]
	seed_doctype("KEK Ref Item Category", item_categories)

	# 3. KEK Ref Customs Document
	customs_docs = [
		{"code": "0407021", "description": "BC 2.1", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407024", "description": "BC 24", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407261", "description": "BC 2.6.1", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407262", "description": "BC 2.6.2", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407027", "description": "BC 2.7", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407032", "description": "BC 3.2", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407033", "description": "BC 3.3", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407034", "description": "BC 3.4", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407040", "description": "BC 4.0", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407041", "description": "BC 4.1", "doc_group": "KEK/FTZ/BC"},
		{"code": "0407051", "description": "FTZ 01", "doc_group": "FTZ"},
		{"code": "0407512", "description": "FTZ01 - Pengeluaran ke LDP", "doc_group": "FTZ"},
		{"code": "0407612", "description": "KEK - Pemasukan Melalui Barang Kiriman", "doc_group": "KEK"},
		{"code": "0407613", "description": "KEK - Pemasukan dari TLDDP", "doc_group": "KEK"},
		{"code": "0407614", "description": "KEK - Pemasukan dari TLDDP Subkon", "doc_group": "KEK"},
		{"code": "0407621", "description": "KEK - Pengeluaran ke KEK/TPB/FTZP", "doc_group": "KEK"},
		{"code": "0407631", "description": "KEK - Pengeluaran ke LDP", "doc_group": "KEK"},
		{"code": "0407633", "description": "KEK - Pengeluaran ke TLDDP Subkon", "doc_group": "KEK"},
		{"code": "0407634", "description": "KEK - Pengeluaran ke TLDDP Ex 613", "doc_group": "KEK"},
		{"code": "0407008", "description": "Free Movement", "doc_group": "Movement"}
	]
	seed_doctype("KEK Ref Customs Document", customs_docs)

	# 4. KEK Ref Unit
	units = [
		{"code": "KGM", "description": "kilogram"},
		{"code": "GRM", "description": "gram"},
		{"code": "LTR", "description": "litre"},
		{"code": "PCE", "description": "piece"},
		{"code": "SET", "description": "set"}
	]
	seed_doctype("KEK Ref Unit", units)

	# 5. KEK Ref Activity Code
	activity_codes = [
		{"code": "30", "description": "Incoming Goods"},
		{"code": "31", "description": "Outgoing Goods"},
		{"code": "32", "description": "Stock Opname Goods"},
		{"code": "33", "description": "Adjustment Goods"}
	]
	seed_doctype("KEK Ref Activity Code", activity_codes)

def seed_doctype(doctype, data):
	for item in data:
		if not frappe.db.exists(doctype, item["code"]):
			doc = frappe.get_doc({
				"doctype": doctype,
				**item
			})
			doc.insert(ignore_permissions=True)
			print(f"Seeded {doctype}: {item['code']}")
		else:
			print(f"Skipped {doctype}: {item['code']} (Already exists)")
	frappe.db.commit()
