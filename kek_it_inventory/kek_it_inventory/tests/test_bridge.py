import frappe
import unittest
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

class TestBridge(unittest.TestCase):
	def setUp(self):
		# Create a company profile for 'bcmerak'
		if not frappe.db.exists("KEK Company Profile", "BC MERAK PROFILE"):
			self.profile = frappe.get_doc({
				"doctype": "KEK Company Profile",
				"company_name": "BC MERAK PROFILE",
				"npwp": "012345678901234",
				"erpnext_company": "bcmerak"
			}).insert()
		
		# Ensure Unit 'Nos' exists for testing
		if not frappe.db.exists("KEK Ref Unit", "Nos"):
			frappe.get_doc({
				"doctype": "KEK Ref Unit",
				"code": "Nos",
				"description": "Numbers"
			}).insert()
		
		# Create a warehouse for 'bcmerak' if not exists
		if not frappe.db.exists("Warehouse", "Test KEK Warehouse - BCM"):
			frappe.get_doc({
				"doctype": "Warehouse",
				"warehouse_name": "Test KEK Warehouse",
				"company": "bcmerak"
			}).insert()

	def tearDown(self):
		frappe.db.rollback()

	def test_purchase_receipt_bridge_with_mapping(self):
		# 1. Create a Mapping for a specific item
		test_item = "_Test Item" # Standard ERPNext test item
		if not frappe.db.exists("KEK Item Mapping", {"erpnext_item": test_item}):
			frappe.get_doc({
				"doctype": "KEK Item Mapping",
				"erpnext_item": test_item,
				"customs_item_code": "CUSTOMS-CODE-ABC",
				"customs_item_name": "Sharp Customs Name"
			}).insert()

		# 2. Create and Submit a Purchase Receipt
		pr = make_purchase_receipt(
			company="bcmerak", 
			qty=5, 
			item_code=test_item,
			warehouse="Test KEK Warehouse - BCM"
		)
		pr.submit()

		# 3. Verify KEK Transaction used the mapped code
		kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", 
			{"erpnext_reference_name": pr.name}, "name")
		
		doc = frappe.get_doc("KEK Inventory Transaction", kek_txn_name)
		self.assertEqual(doc.items[0].customs_item_code, "CUSTOMS-CODE-ABC")
		# self.assertEqual(doc.items[0].customs_item_name, "Sharp Customs Name") # Assuming field exists
