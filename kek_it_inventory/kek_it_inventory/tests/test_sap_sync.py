import frappe
import unittest
from kek_it_inventory.kek_it_inventory.api.sap_sync import normalize_uom, process_sap_document_async

class TestSAPSync(unittest.TestCase):
	def setUp(self):
		# Ensure a test item exists
		if not frappe.db.exists("Item", "SAP-TEST-ITEM"):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": "SAP-TEST-ITEM",
				"item_group": "All Item Groups",
				"is_stock_item": 1,
				"stock_uom": "Nos"
			}).insert()

		# Ensure a test supplier exists
		if not frappe.db.exists("Supplier", "SAP-TEST-SUPPLIER"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "SAP-TEST-SUPPLIER",
				"supplier_group": "All Supplier Groups"
			}).insert()

		# Ensure a test customer exists
		if not frappe.db.exists("Customer", "SAP-TEST-CUSTOMER"):
			frappe.get_doc({
				"doctype": "Customer",
				"customer_name": "SAP-TEST-CUSTOMER",
				"customer_group": "All Customer Groups",
				"territory": "All Territories"
			}).insert()

		# Ensure warehouse exists
		if not frappe.db.exists("Warehouse", "Test Warehouse - BCM"):
			frappe.get_doc({
				"doctype": "Warehouse",
				"warehouse_name": "Test Warehouse",
				"company": "bcmerak"
			}).insert()

		# Ensure UOMs exist for tests
		for uom in ["Unit", "Box", "Nos", "XYZ"]:
			if not frappe.db.exists("UOM", uom):
				frappe.get_doc({
					"doctype": "UOM",
					"uom_name": uom,
					"name": uom
				}).insert()



	def tearDown(self):
		frappe.db.rollback()

	def test_normalize_uom(self):
		self.assertEqual(normalize_uom("EA"), frappe.db.get_value("UOM", {"name": "Unit"}, "name") or "Unit")
		self.assertEqual(normalize_uom("PC"), frappe.db.get_value("UOM", {"name": "Unit"}, "name") or "Unit")
		self.assertEqual(normalize_uom("BOX"), frappe.db.get_value("UOM", {"name": "Box"}, "name") or "Box")
		self.assertEqual(normalize_uom("XYZ"), frappe.db.get_value("UOM", {"name": "XYZ"}, "name") or "XYZ")



	def test_process_sap_document_async_success(self):
		# Create an Integration Log for testing
		log = frappe.get_doc({
			"doctype": "SAP Integration Log",
			"sap_document_number": "SAP-PO-10001",
			"document_type": "Purchase Order",
			"status": "Pending",
			"sap_payload": frappe.as_json({
				"PurchaseOrder": "SAP-PO-10001",
				"Supplier": "SAP-TEST-SUPPLIER",
				"CompanyCode": "bcmerak",
				"DocumentCurrency": "IDR",
				"CreationDate": "2026-07-06T00:00:00",
				"to_PurchaseOrderItem": {
					"results": [
						{
							"Material": "SAP-TEST-ITEM",
							"OrderQuantity": 10,
							"PurchaseOrderQuantityUnit": "EA",
							"NetPriceAmount": 15000,
							"Plant": "Test Warehouse - BCM",
							"PurchaseOrderItemText": "Test item description"
						}
					]
				}
			})
		}).insert()

		process_sap_document_async(log.name)

		# Refresh log
		log.reload()
		self.assertEqual(log.status, "Success")
		self.assertTrue(log.erpnext_reference)

		# Verify Purchase Order was created
		po = frappe.get_doc("Purchase Order", log.erpnext_reference)
		self.assertEqual(po.supplier, "SAP-TEST-SUPPLIER")
		self.assertEqual(po.custom_sap_po_number, "SAP-PO-10001")
		self.assertEqual(po.items[0].item_code, "SAP-TEST-ITEM")
		self.assertEqual(po.items[0].qty, 10.0)
		self.assertEqual(po.items[0].uom, "Unit")

	def test_idempotency(self):
		# Create a successful log & PO first
		log1 = frappe.get_doc({
			"doctype": "SAP Integration Log",
			"sap_document_number": "SAP-PO-10002",
			"document_type": "Purchase Order",
			"status": "Pending",
			"sap_payload": frappe.as_json({
				"PurchaseOrder": "SAP-PO-10002",
				"Supplier": "SAP-TEST-SUPPLIER",
				"CompanyCode": "bcmerak",
				"DocumentCurrency": "IDR",
				"CreationDate": "2026-07-06T00:00:00",
				"to_PurchaseOrderItem": {
					"results": [
						{
							"Material": "SAP-TEST-ITEM",
							"OrderQuantity": 5,
							"PurchaseOrderQuantityUnit": "EA",
							"NetPriceAmount": 12000,
							"Plant": "Test Warehouse - BCM"
						}
					]
				}
			})
		}).insert()

		process_sap_document_async(log1.name)
		log1.reload()
		self.assertEqual(log1.status, "Success")

		# Try to process another log with the same PO number
		log2 = frappe.get_doc({
			"doctype": "SAP Integration Log",
			"sap_document_number": "SAP-PO-10002",
			"document_type": "Purchase Order",
			"status": "Pending",
			"sap_payload": log1.sap_payload
		}).insert()

		process_sap_document_async(log2.name)
		log2.reload()

		# It should succeed by linking to the existing PO instead of creating a duplicate
		self.assertEqual(log2.status, "Success")
		self.assertEqual(log2.erpnext_reference, log1.erpnext_reference)

	def test_missing_master_data_fail(self):
		log = frappe.get_doc({
			"doctype": "SAP Integration Log",
			"sap_document_number": "SAP-PO-10003",
			"document_type": "Purchase Order",
			"status": "Pending",
			"sap_payload": frappe.as_json({
				"PurchaseOrder": "SAP-PO-10003",
				"Supplier": "NON-EXISTENT-SUPPLIER",
				"CompanyCode": "bcmerak",
				"DocumentCurrency": "IDR",
				"CreationDate": "2026-07-06T00:00:00",
				"to_PurchaseOrderItem": {
					"results": [
						{
							"Material": "SAP-TEST-ITEM",
							"OrderQuantity": 5,
							"PurchaseOrderQuantityUnit": "EA",
							"NetPriceAmount": 12000,
							"Plant": "Test Warehouse - BCM"
						}
					]
				}
			})
		}).insert()

		process_sap_document_async(log.name)
		log.reload()

		self.assertEqual(log.status, "Failed")
		self.assertIn("Supplier NON-EXISTENT-SUPPLIER not found", log.error_trace)

	def test_process_sales_order_async_success(self):
		log = frappe.get_doc({
			"doctype": "SAP Integration Log",
			"sap_document_number": "SAP-SO-10001",
			"document_type": "Sales Order",
			"status": "Pending",
			"sap_payload": frappe.as_json({
				"SalesOrder": "SAP-SO-10001",
				"Customer": "SAP-TEST-CUSTOMER",
				"CompanyCode": "bcmerak",
				"DocumentCurrency": "IDR",
				"CreationDate": "2026-07-06T00:00:00",
				"to_SalesOrderItem": {
					"results": [
						{
							"Material": "SAP-TEST-ITEM",
							"OrderQuantity": 15,
							"OrderQuantityUnit": "EA",
							"NetPriceAmount": 20000,
							"Plant": "Test Warehouse - BCM",
							"SalesOrderItemText": "Test SO description"
						}
					]
				}
			})
		}).insert()

		process_sap_document_async(log.name)
		log.reload()

		self.assertEqual(log.status, "Success")
		self.assertTrue(log.erpnext_reference)

		so = frappe.get_doc("Sales Order", log.erpnext_reference)
		self.assertEqual(so.customer, "SAP-TEST-CUSTOMER")
		self.assertEqual(so.custom_sap_so_number, "SAP-SO-10001")
		self.assertEqual(so.items[0].item_code, "SAP-TEST-ITEM")
		self.assertEqual(so.items[0].qty, 15.0)
		self.assertEqual(so.items[0].uom, "Unit")

