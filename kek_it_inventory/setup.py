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
		{"code": "0407611", "description": "KEK - Pemasukan dari LDP", "doc_group": "KEK"},
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

	# 6. Create custom fields for integration
	create_kek_custom_fields()

	# 7. Setup Test Role Permissions
	from kek_it_inventory.setup_role import setup_test_role_permissions
	setup_test_role_permissions()

	# 8. Setup KEK Manager Permissions
	from kek_it_inventory.setup_role import setup_kek_manager_permissions
	setup_kek_manager_permissions()

	# 9. Setup KEK User Permissions
	from kek_it_inventory.setup_role import setup_kek_user_permissions
	setup_kek_user_permissions()



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

def create_kek_custom_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	custom_fields = {
		"Purchase Order": [
			{
				"fieldname": "kek_section",
				"fieldtype": "Section Break",
				"label": "KEK IT Inventory Integration",
				"hidden": 0,
				"insert_after": "status"
			},
			{
				"fieldname": "kek_status",
				"fieldtype": "Select",
				"label": "KEK Status",
				"options": "\nQUEUED\nSENT\nACKNOWLEDGED\nFAILED\nPENDING\nMISMATCH\nBYPASSED\nValidated",
				"read_only": 1,
				"hidden": 0,
				"insert_after": "kek_section"
			},
			{
				"fieldname": "kek_transaction",
				"fieldtype": "Link",
				"label": "KEK Transaction",
				"options": "KEK Inventory Transaction",
				"read_only": 1,
				"hidden": 1,
				"insert_after": "kek_status"
			},
			{
				"fieldname": "nomor_ppkek",
				"fieldtype": "Data",
				"label": "Nomor PPKEK",
				"read_only": 0,
				"hidden": 0,
				"allow_on_submit": 1,
				"insert_after": "kek_transaction"
			},
			{
				"fieldname": "tanggal_ppkek",
				"fieldtype": "Date",
				"label": "Tanggal PPKEK",
				"read_only": 0,
				"hidden": 0,
				"allow_on_submit": 1,
				"insert_after": "nomor_ppkek"
			}
		],
		"Subcontracting Order": [
			{
				"fieldname": "kek_section",
				"fieldtype": "Section Break",
				"label": "KEK IT Inventory Integration",
				"hidden": 0,
				"insert_after": "status"
			},
			{
				"fieldname": "kek_status",
				"fieldtype": "Select",
				"label": "KEK Status",
				"options": "\nQUEUED\nSENT\nACKNOWLEDGED\nFAILED\nPENDING\nMISMATCH\nBYPASSED\nValidated",
				"read_only": 1,
				"hidden": 0,
				"insert_after": "kek_section"
			},
			{
				"fieldname": "kek_transaction",
				"fieldtype": "Link",
				"label": "KEK Transaction",
				"options": "KEK Inventory Transaction",
				"read_only": 1,
				"hidden": 1,
				"insert_after": "kek_status"
			},
			{
				"fieldname": "nomor_ppkek",
				"fieldtype": "Data",
				"label": "Nomor PPKEK",
				"read_only": 0,
				"hidden": 0,
				"allow_on_submit": 1,
				"insert_after": "kek_transaction"
			},
			{
				"fieldname": "tanggal_ppkek",
				"fieldtype": "Date",
				"label": "Tanggal PPKEK",
				"read_only": 0,
				"hidden": 0,
				"allow_on_submit": 1,
				"insert_after": "nomor_ppkek"
			}
		],
		"Purchase Receipt": [
			{
				"fieldname": "kek_section",
				"fieldtype": "Section Break",
				"label": "KEK IT Inventory Integration",
				"insert_after": "status"
			},
			{
				"fieldname": "kek_status",
				"fieldtype": "Select",
				"label": "KEK Status",
				"options": "\nQUEUED\nSENT\nACKNOWLEDGED\nFAILED\nPENDING\nMISMATCH\nBYPASSED\nValidated",
				"read_only": 1,
				"insert_after": "kek_section"
			},
			{
				"fieldname": "kek_transaction",
				"fieldtype": "Link",
				"label": "KEK Transaction",
				"options": "KEK Inventory Transaction",
				"insert_after": "kek_status"
			},
			{
				"fieldname": "nomor_ppkek",
				"fieldtype": "Data",
				"label": "Nomor PPKEK",
				"read_only": 0,
				"allow_on_submit": 1,
				"insert_after": "kek_transaction"
			},
			{
				"fieldname": "tanggal_ppkek",
				"fieldtype": "Date",
				"label": "Tanggal PPKEK",
				"read_only": 0,
				"allow_on_submit": 1,
				"insert_after": "nomor_ppkek"
			},
			{
				"fieldname": "kek_insw_id",
				"fieldtype": "Data",
				"label": "KEK INSW ID",
				"read_only": 1,
				"insert_after": "nomor_ppkek"
			},
			{
				"fieldname": "kek_error",
				"fieldtype": "Small Text",
				"label": "KEK Error Message",
				"read_only": 1,
				"insert_after": "kek_insw_id"
			},
			{
				"fieldname": "bypass_kek_validation",
				"fieldtype": "Check",
				"label": "Bypass KEK Validation",
				"insert_after": "kek_error"
			},
			{
				"fieldname": "bypass_reason",
				"fieldtype": "Small Text",
				"label": "Bypass Reason",
				"insert_after": "bypass_kek_validation"
			}
		],
		"Delivery Note": [
			{
				"fieldname": "kek_section",
				"fieldtype": "Section Break",
				"label": "KEK IT Inventory Integration",
				"insert_after": "status"
			},
			{
				"fieldname": "kek_status",
				"fieldtype": "Select",
				"label": "KEK Status",
				"options": "\nQUEUED\nSENT\nACKNOWLEDGED\nFAILED\nPENDING\nMISMATCH\nBYPASSED\nValidated",
				"read_only": 1,
				"insert_after": "kek_section"
			},
			{
				"fieldname": "kek_transaction",
				"fieldtype": "Link",
				"label": "KEK Transaction",
				"options": "KEK Inventory Transaction",
				"insert_after": "kek_status"
			},
			{
				"fieldname": "nomor_ppkek",
				"fieldtype": "Data",
				"label": "Nomor PPKEK",
				"read_only": 0,
				"allow_on_submit": 1,
				"insert_after": "kek_transaction"
			},
			{
				"fieldname": "tanggal_ppkek",
				"fieldtype": "Date",
				"label": "Tanggal PPKEK",
				"read_only": 0,
				"allow_on_submit": 1,
				"insert_after": "nomor_ppkek"
			},
			{
				"fieldname": "kek_insw_id",
				"fieldtype": "Data",
				"label": "KEK INSW ID",
				"read_only": 1,
				"insert_after": "nomor_ppkek"
			},
			{
				"fieldname": "kek_error",
				"fieldtype": "Small Text",
				"label": "KEK Error Message",
				"read_only": 1,
				"insert_after": "kek_insw_id"
			},
			{
				"fieldname": "bypass_kek_validation",
				"fieldtype": "Check",
				"label": "Bypass KEK Validation",
				"insert_after": "kek_error"
			},
			{
				"fieldname": "bypass_reason",
				"fieldtype": "Small Text",
				"label": "Bypass Reason",
				"insert_after": "bypass_kek_validation"
			}
		],
		"Subcontracting Receipt": [
			{
				"fieldname": "kek_section",
				"fieldtype": "Section Break",
				"label": "KEK IT Inventory Integration",
				"insert_after": "status"
			},
			{
				"fieldname": "kek_status",
				"fieldtype": "Select",
				"label": "KEK Status",
				"options": "\nQUEUED\nSENT\nACKNOWLEDGED\nFAILED\nPENDING\nMISMATCH\nBYPASSED\nValidated",
				"read_only": 1,
				"insert_after": "kek_section"
			},
			{
				"fieldname": "kek_transaction",
				"fieldtype": "Link",
				"label": "KEK Transaction",
				"options": "KEK Inventory Transaction",
				"insert_after": "kek_status"
			},
			{
				"fieldname": "nomor_ppkek",
				"fieldtype": "Data",
				"label": "Nomor PPKEK",
				"read_only": 0,
				"allow_on_submit": 1,
				"insert_after": "kek_transaction"
			},
			{
				"fieldname": "tanggal_ppkek",
				"fieldtype": "Date",
				"label": "Tanggal PPKEK",
				"read_only": 0,
				"allow_on_submit": 1,
				"insert_after": "nomor_ppkek"
			},
			{
				"fieldname": "kek_insw_id",
				"fieldtype": "Data",
				"label": "KEK INSW ID",
				"read_only": 1,
				"insert_after": "nomor_ppkek"
			},
			{
				"fieldname": "kek_error",
				"fieldtype": "Small Text",
				"label": "KEK Error Message",
				"read_only": 1,
				"insert_after": "kek_insw_id"
			},
			{
				"fieldname": "bypass_kek_validation",
				"fieldtype": "Check",
				"label": "Bypass KEK Validation",
				"insert_after": "kek_error"
			},
			{
				"fieldname": "bypass_reason",
				"fieldtype": "Small Text",
				"label": "Bypass Reason",
				"insert_after": "bypass_kek_validation"
			}
		]
	}
	create_custom_fields(custom_fields, ignore_validate=True)
	frappe.db.commit()
