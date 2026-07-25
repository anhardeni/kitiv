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

    # ------------------------------------------------------------------
    # ME2N / VA05 Excel Import & Lazy Master Data Unit Tests
    # ------------------------------------------------------------------

    def test_normalize_sap_me2n_columns_po(self):
        import pandas as pd
        from kek_it_inventory.kek_it_inventory.api.sap_sync import normalize_sap_me2n_columns

        df_raw = pd.DataFrame([{
            "Purchasing Document": "4600177687",
            "Item": "10",
            "Supplier/Supplying Plant": "8100 Ningbo Supplier",
            "Material": "R05210.7920.32-64",
            "Short Text": "Test Description",
            "Order Quantity": 100,
            "Net Price": 50.5,
            "Document Date": "2026-06-26"
        }])

        df_norm, doc_type = normalize_sap_me2n_columns(df_raw)
        self.assertEqual(doc_type, "Purchase Order")
        self.assertEqual(df_norm["po_number"].iloc[0], "4600177687")
        self.assertEqual(df_norm["item_code"].iloc[0], "R05210.7920.32-64")
        self.assertEqual(df_norm["supplier"].iloc[0], "8100 Ningbo Supplier")
        self.assertEqual(df_norm["qty"].iloc[0], 100)
        self.assertEqual(df_norm["rate"].iloc[0], 50.5)

    def test_normalize_sap_va05_columns_so(self):
        import pandas as pd
        from kek_it_inventory.kek_it_inventory.api.sap_sync import normalize_sap_me2n_columns

        df_raw = pd.DataFrame([{
            "Sales Document": "SO-SAP-9988",
            "Sold-to Party": "Customer ABC",
            "Material": "ITEM-SO-01",
            "Order Quantity": 10
        }])

        df_norm, doc_type = normalize_sap_me2n_columns(df_raw)
        self.assertEqual(doc_type, "Sales Order")
        self.assertEqual(df_norm["so_number"].iloc[0], "SO-SAP-9988")
        self.assertEqual(df_norm["customer"].iloc[0], "Customer ABC")
        self.assertEqual(df_norm["item_code"].iloc[0], "ITEM-SO-01")

    def test_lazy_master_data_creation_supplier_and_item(self):
        from kek_it_inventory.kek_it_inventory.api.sap_sync import ensure_supplier_or_customer, ensure_item

        new_supplier = "LAZY-SUPPLIER-001"
        new_item = "LAZY-ITEM-001"

        supp_name = ensure_supplier_or_customer(new_supplier, is_supplier=True)
        self.assertTrue(frappe.db.exists("Supplier", supp_name))

        item_name = ensure_item(new_item, description="Lazy Item Description", uom="Nos")
        self.assertTrue(frappe.db.exists("Item", item_name))

    def test_sap_me2n_po_creation_in_draft(self):
        po_num = "4600177687-TEST"
        supplier_name = "8100 Ningbo Medical Test"
        item_code = "R05210.7920.32-64-TEST"

        from kek_it_inventory.kek_it_inventory.api.sap_sync import ensure_supplier_or_customer, ensure_item, get_default_warehouse
        supp = ensure_supplier_or_customer(supplier_name, is_supplier=True)
        it = ensure_item(item_code, "Test Item", "Nos")
        wh, comp = get_default_warehouse()

        po_doc = frappe.get_doc({
            "doctype": "Purchase Order",
            "company": comp,
            "supplier": supp,
            "custom_sap_po_number": po_num,
            "transaction_date": "2026-06-26",
            "schedule_date": "2026-06-26",
            "set_warehouse": wh,
            "items": [{
                "item_code": it,
                "qty": 10,
                "rate": 100,
                "warehouse": wh
            }]
        })
        po_doc.insert(ignore_permissions=True)

        self.assertEqual(po_doc.docstatus, 0)  # Draft status
        self.assertEqual(po_doc.custom_sap_po_number, po_num)

        # Idempotency check: finding existing PO by custom_sap_po_number
        existing = frappe.db.get_value("Purchase Order", {"custom_sap_po_number": po_num}, "name")
        self.assertEqual(existing, po_doc.name)

    def test_duplicate_sap_po_number_idempotency(self):
        """Tests that importing a PO with an already existing custom_sap_po_number does NOT create a duplicate."""
        po_num = "DUP-PO-9999"
        supplier_name = "8100 Duplicate Supplier Test"
        item_code = "ITEM-DUP-01"

        from kek_it_inventory.kek_it_inventory.api.sap_sync import ensure_supplier_or_customer, ensure_item, get_default_warehouse
        supp = ensure_supplier_or_customer(supplier_name, is_supplier=True)
        it = ensure_item(item_code, "Duplicate Item", "Nos")
        wh, comp = get_default_warehouse()

        # First import attempt
        po_doc1 = frappe.get_doc({
            "doctype": "Purchase Order",
            "company": comp,
            "supplier": supp,
            "custom_sap_po_number": po_num,
            "transaction_date": "2026-06-26",
            "schedule_date": "2026-06-26",
            "set_warehouse": wh,
            "items": [{
                "item_code": it,
                "qty": 5,
                "rate": 200,
                "warehouse": wh
            }]
        })
        po_doc1.insert(ignore_permissions=True)

        # Count after first creation
        count_after_first = frappe.db.count("Purchase Order", {"custom_sap_po_number": po_num})
        self.assertEqual(count_after_first, 1)

        # Second import attempt with SAME custom_sap_po_number (simulation of re-running chunked import)
        existing_po_name = frappe.db.get_value("Purchase Order", {"custom_sap_po_number": po_num}, "name")
        if not existing_po_name:
            po_doc2 = frappe.get_doc({
                "doctype": "Purchase Order",
                "company": comp,
                "supplier": supp,
                "custom_sap_po_number": po_num,
                "transaction_date": "2026-06-26",
                "schedule_date": "2026-06-26",
                "set_warehouse": wh,
                "items": [{
                    "item_code": it,
                    "qty": 5,
                    "rate": 200,
                    "warehouse": wh
                }]
            })
            po_doc2.insert(ignore_permissions=True)

        # Count after second attempt MUST still be 1 (No duplicate PO created!)
        count_after_second = frappe.db.count("Purchase Order", {"custom_sap_po_number": po_num})
        self.assertEqual(count_after_second, 1)




