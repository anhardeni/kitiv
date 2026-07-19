# -*- coding: utf-8 -*-
import frappe
import unittest
import json
from kek_it_inventory.kek_it_inventory.sap_connector.utils import parse_sap_odata_date, parse_sap_string_decimal
from kek_it_inventory.kek_it_inventory.sap_connector.mapping_engine import execute_live_sap_sync_from_push

class TestSAPSync(unittest.TestCase):

    CONFIG_NAME = "TEST-PO-STREAM"
    CONFIG_NAME_SO = "TEST-SO-STREAM"

    def setUp(self):
        # Ensure test Item
        if not frappe.db.exists("Item", "SAP-TEST-ITEM"):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": "SAP-TEST-ITEM",
                "item_group": "All Item Groups",
                "is_stock_item": 1,
                "stock_uom": "Nos"
            }).insert()

        # Ensure test Supplier
        if not frappe.db.exists("Supplier", "SAP-TEST-SUPPLIER"):
            frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": "SAP-TEST-SUPPLIER",
                "supplier_group": "All Supplier Groups"
            }).insert()

        # Ensure test Customer
        if not frappe.db.exists("Customer", "SAP-TEST-CUSTOMER"):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "SAP-TEST-CUSTOMER",
                "customer_group": "All Customer Groups",
                "territory": "All Territories"
            }).insert()

        # Ensure UOMs
        for uom in ["Unit", "Box", "Nos"]:
            if not frappe.db.exists("UOM", uom):
                frappe.get_doc({"doctype": "UOM", "uom_name": uom, "name": uom}).insert()

        # Ensure SAP Integration Config for PO
        if not frappe.db.exists("SAP Integration Config", self.CONFIG_NAME):
            frappe.get_doc({
                "doctype": "SAP Integration Config",
                "stream_name": self.CONFIG_NAME,
                "erpnext_target_doctype": "Purchase Order",
                "po_endpoint": "http://localhost/sap/po",
                "connection_and_auth": json.dumps({"user": "test", "pass": "test"}),
                "sap_child_array_key": "to_PurchaseOrderItem",
                "field_mappings": [
                    {"sap_field": "PurchaseOrder", "erpnext_field": "custom_sap_po_number", "table_level": "Header", "data_type": "String"},
                    {"sap_field": "DocumentCurrency", "erpnext_field": "currency", "table_level": "Header", "data_type": "String"},
                    {"sap_field": "CreationDate", "erpnext_field": "transaction_date", "table_level": "Header", "data_type": "String"},
                    {"sap_field": "OrderQuantity", "erpnext_field": "qty", "table_level": "Item", "data_type": "Decimal"},
                    {"sap_field": "NetPriceAmount", "erpnext_field": "rate", "table_level": "Item", "data_type": "Decimal"},
                ]
            }).insert()

        # Ensure SAP Integration Config for SO
        if not frappe.db.exists("SAP Integration Config", self.CONFIG_NAME_SO):
            frappe.get_doc({
                "doctype": "SAP Integration Config",
                "stream_name": self.CONFIG_NAME_SO,
                "erpnext_target_doctype": "Sales Order",
                "po_endpoint": "http://localhost/sap/so",
                "connection_and_auth": json.dumps({"user": "test", "pass": "test"}),
                "sap_child_array_key": "to_SalesOrderItem",
                "field_mappings": [
                    {"sap_field": "SalesOrder", "erpnext_field": "custom_sap_so_number", "table_level": "Header", "data_type": "String"},
                    {"sap_field": "DocumentCurrency", "erpnext_field": "currency", "table_level": "Header", "data_type": "String"},
                    {"sap_field": "CreationDate", "erpnext_field": "transaction_date", "table_level": "Header", "data_type": "String"},
                    {"sap_field": "OrderQuantity", "erpnext_field": "qty", "table_level": "Item", "data_type": "Decimal"},
                    {"sap_field": "NetPriceAmount", "erpnext_field": "rate", "table_level": "Item", "data_type": "Decimal"},
                ]
            }).insert()

    def tearDown(self):
        frappe.db.rollback()

    # ------------------------------------------------------------------
    # Utils Tests
    # ------------------------------------------------------------------

    def test_parse_sap_odata_date_valid(self):
        result = parse_sap_odata_date("/Date(1753920000000)/")
        self.assertIsNotNone(result)
        self.assertRegex(result, r"\d{4}-\d{2}-\d{2}")

    def test_parse_sap_odata_date_plain_string(self):
        self.assertEqual(parse_sap_odata_date("2026-07-19"), "2026-07-19")

    def test_parse_sap_odata_date_none(self):
        self.assertIsNone(parse_sap_odata_date(None))

    def test_parse_sap_string_decimal_standard(self):
        self.assertAlmostEqual(parse_sap_string_decimal("1500.50"), 1500.50)

    def test_parse_sap_string_decimal_european(self):
        self.assertAlmostEqual(parse_sap_string_decimal("1.500,50"), 1500.50)

    def test_parse_sap_string_decimal_none(self):
        self.assertEqual(parse_sap_string_decimal(None), 0.0)

    # ------------------------------------------------------------------
    # Push Handler Tests (Purchase Order)
    # ------------------------------------------------------------------

    def _make_log(self, sap_id):
        log = frappe.new_doc("SAP Integration Log")
        log.sap_po_id = sap_id
        log.sync_status = "Failed"
        log.execution_time = frappe.utils.now_datetime()
        log.insert(ignore_permissions=True)
        frappe.db.commit()
        return log.name

    def test_push_purchase_order_success(self):
        sap_id = "SAP-PO-TEST-001"
        log_name = self._make_log(sap_id)

        payload = {
            "PurchaseOrder": sap_id,
            "Supplier": "SAP-TEST-SUPPLIER",
            "DocumentCurrency": "IDR",
            "CreationDate": "2026-07-19",
            "to_PurchaseOrderItem": {"results": [{
                "Material": "SAP-TEST-ITEM",
                "OrderQuantity": 5,
                "PurchaseOrderQuantityUnit": "EA",
                "NetPriceAmount": 10000,
            }]}
        }

        execute_live_sap_sync_from_push(log_name, payload)

        log = frappe.get_doc("SAP Integration Log", log_name)
        self.assertEqual(log.sync_status, "Success")

    def test_push_purchase_order_idempotency(self):
        sap_id = "SAP-PO-TEST-002"
        log_name_1 = self._make_log(sap_id)

        payload = {
            "PurchaseOrder": sap_id,
            "Supplier": "SAP-TEST-SUPPLIER",
            "DocumentCurrency": "IDR",
            "CreationDate": "2026-07-19",
            "to_PurchaseOrderItem": {"results": [{
                "Material": "SAP-TEST-ITEM",
                "OrderQuantity": 3,
                "PurchaseOrderQuantityUnit": "EA",
                "NetPriceAmount": 8000,
            }]}
        }

        execute_live_sap_sync_from_push(log_name_1, payload)

        # Second push of same PO — should succeed without creating duplicate
        log_name_2 = self._make_log(sap_id)
        execute_live_sap_sync_from_push(log_name_2, payload)
        log2 = frappe.get_doc("SAP Integration Log", log_name_2)
        self.assertEqual(log2.sync_status, "Success")

    def test_push_no_config_fails(self):
        # A doctype with no matching config → should log as Failed
        sap_id = "SAP-UNKNOWN-99"
        log_name = self._make_log(sap_id)

        payload = {
            "SomeOtherDocType": sap_id,
        }

        execute_live_sap_sync_from_push(log_name, payload)

        log = frappe.get_doc("SAP Integration Log", log_name)
        # No PurchaseOrder or SalesOrder key → config not found
        self.assertEqual(log.sync_status, "Failed")

    # ------------------------------------------------------------------
    # Utils Validator Tests
    # ------------------------------------------------------------------

    def test_run_automated_mapping_check_valid(self):
        from kek_it_inventory.kek_it_inventory.sap_connector.validator import run_automated_mapping_check
        result = run_automated_mapping_check(json.dumps({"PurchaseOrder": "X", "Supplier": "Y"}))
        self.assertEqual(result["status"], "Success")
        self.assertIn("PASS", result["html_report"])

    def test_run_automated_mapping_check_invalid_json(self):
        from kek_it_inventory.kek_it_inventory.sap_connector.validator import run_automated_mapping_check
        result = run_automated_mapping_check("{NOT JSON}")
        self.assertEqual(result["status"], "Failed")
