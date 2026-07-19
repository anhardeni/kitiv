# -*- coding: utf-8 -*-
import frappe
import requests
import json
from requests.auth import HTTPBasicAuth
from kek_it_inventory.kek_it_inventory.sap_connector.utils import parse_sap_odata_date, parse_sap_string_decimal

def _resolve_party(doctype, sap_code_field, name_field, sap_value):
    """
    Resolve a SAP party code (Supplier/Customer) to an ERPNext document name.
    Falls back gracefully when custom SAP code columns haven't been created yet.
    Priority: custom SAP code field → exact name match → name_field match
    """
    resolved = None
    # 1. Try custom SAP field (only if the column exists in DB)
    if frappe.db.has_column(doctype, sap_code_field):
        resolved = frappe.db.get_value(doctype, {sap_code_field: sap_value}, "name")
    # 2. Exact name (document name) match
    if not resolved:
        resolved = frappe.db.get_value(doctype, {"name": sap_value}, "name")
    # 3. Human-readable name field (e.g. supplier_name, customer_name)
    if not resolved:
        resolved = frappe.db.get_value(doctype, {name_field: sap_value}, "name")
    return resolved

def _get_default_warehouse(item_code, company):
    """Safely retrieves a default warehouse for the given item and company."""
    # 1. Try item-level default warehouse
    if frappe.db.has_column("Item", "default_warehouse"):
        wh = frappe.db.get_value("Item", item_code, "default_warehouse")
        if wh:
            return wh
    # 2. Try item default warehouse for the specific company
    wh = frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, "default_warehouse")
    if wh:
        return wh
    # 3. Try standard "Stores" or "Finished Goods" or "Work In Progress" for the company
    for name in ["Stores", "All Warehouses", "Finished Goods", "Gudang Utama"]:
        wh_name = f"{name} - {frappe.get_cached_value('Company', company, 'abbr')}"
        if frappe.db.exists("Warehouse", wh_name):
            return wh_name
    # 4. Fallback to any warehouse in the database
    any_wh = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
    return any_wh


def execute_hourly_sync():
    """Memicu sinkronisasi terjadwal untuk seluruh data stream aktif"""
    active_streams = frappe.get_all("SAP Integration Config", fields=["name"])
    for stream in active_streams:
        execute_live_sap_sync(stream.name)

def execute_live_sap_sync_from_push(log_name, raw_payload):
    """
    Handle a PUSH from SAP. Finds the matching SAP Integration Config by
    target doctype (Purchase Order or Sales Order), then applies dynamic
    field mapping and writes back the audit log result.
    """
    sap_id = str(raw_payload.get("PurchaseOrder") or raw_payload.get("SalesOrder") or raw_payload.get("DocNum") or "")
    target_doctype = "Purchase Order" if raw_payload.get("PurchaseOrder") else "Sales Order"

    # Find the matching config for this doctype
    configs = frappe.get_all(
        "SAP Integration Config",
        filters={"erpnext_target_doctype": target_doctype},
        fields=["name"]
    )
    if not configs:
        _fail_log(log_name, f"No SAP Integration Config found for target doctype '{target_doctype}'")
        return

    config_name = configs[0].name

    try:
        config = frappe.get_doc("SAP Integration Config", config_name)
        default_company = config.get("default_company") or frappe.defaults.get_user_default("company")
        default_currency = config.get("default_currency") or "IDR"

        unique_target_field = next(
            (r.erpnext_field for r in config.field_mappings if r.table_level == "Header" and "sap_" in r.erpnext_field),
            None
        )
        if not unique_target_field:
            unique_target_field = "custom_sap_so_number" if target_doctype == "Sales Order" else "custom_sap_po_number"

        if frappe.db.exists(target_doctype, {unique_target_field: sap_id}):
            _success_log(log_name, raw_payload)
            return

        frappe.db.begin()
        new_erp_doc = frappe.new_doc(target_doctype)
        new_erp_doc.set(unique_target_field, sap_id)
        new_erp_doc.company = default_company
        new_erp_doc.currency = default_currency

        sap_party = raw_payload.get("Customer") or raw_payload.get("SoldToParty") or raw_payload.get("Supplier") or raw_payload.get("CardCode")
        if target_doctype == "Sales Order":
            resolved_party = _resolve_party("Customer", "sap_customer_code", "customer_name", sap_party)
            if not resolved_party:
                raise frappe.ValidationError(f"Customer SAP '{sap_party}' tidak ditemukan di ERPNext.")
            new_erp_doc.customer = resolved_party
        else:
            resolved_party = _resolve_party("Supplier", "sap_vendor_code", "supplier_name", sap_party)
            if not resolved_party:
                raise frappe.ValidationError(f"Supplier SAP '{sap_party}' tidak ditemukan di ERPNext.")
            new_erp_doc.supplier = resolved_party

        header_rules = [r for r in config.field_mappings if r.table_level == "Header" and r.erpnext_field not in ['supplier', 'customer', 'company', 'currency']]
        for rule in header_rules:
            raw_val = raw_payload.get(rule.sap_field)
            new_erp_doc.set(rule.erpnext_field, sanitize_dynamic_value(raw_val, rule.data_type))

        if not new_erp_doc.get("transaction_date"):
            new_erp_doc.transaction_date = frappe.utils.today()
        if target_doctype == "Sales Order" and not new_erp_doc.get("delivery_date"):
            new_erp_doc.delivery_date = frappe.utils.add_days(new_erp_doc.transaction_date, 3)

        child_key = config.sap_child_array_key or ("DocumentLines" if "DocumentLines" in raw_payload else "to_PurchaseOrderItem")
        line_items = raw_payload.get(child_key, {})
        if isinstance(line_items, dict) and "results" in line_items:
            line_items = line_items.get("results", [])

        for sap_item in line_items:
            sap_mat = sap_item.get("Material") or sap_item.get("ItemCode")
            erpnext_item = frappe.db.get_value("Item", {"item_code": sap_mat}, "name")
            if not erpnext_item:
                raise frappe.ValidationError(f"Material SAP '{sap_mat}' tidak terdaftar di ERPNext.")
            item_row = {"item_code": erpnext_item}
            item_rules = [r for r in config.field_mappings if r.table_level == "Item"]
            for rule in item_rules:
                raw_val = sap_item.get(rule.sap_field)
                item_row[rule.erpnext_field] = sanitize_dynamic_value(raw_val, rule.data_type)
            if target_doctype == "Sales Order" and not item_row.get("delivery_date"):
                item_row["delivery_date"] = new_erp_doc.delivery_date
            if target_doctype == "Purchase Order" and not item_row.get("schedule_date"):
                item_row["schedule_date"] = new_erp_doc.transaction_date or frappe.utils.today()
            if not item_row.get("warehouse"):
                item_row["warehouse"] = _get_default_warehouse(erpnext_item, default_company)
            new_erp_doc.append("items", item_row)

        new_erp_doc.insert(ignore_permissions=True)
        _success_log(log_name, raw_payload)
        frappe.db.commit()

    except Exception:
        frappe.db.rollback()
        _fail_log(log_name, frappe.get_traceback(), raw_payload)

def _success_log(log_name, raw_payload=None):
    try:
        log = frappe.get_doc("SAP Integration Log", log_name)
        log.sync_status = "Success"
        log.error_message = None
        if raw_payload:
            log.raw_payload = json.dumps(raw_payload, indent=4)
        log.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(title="SAP Log Update Error", message=frappe.get_traceback())

def _fail_log(log_name, message, raw_payload=None):
    try:
        log = frappe.get_doc("SAP Integration Log", log_name)
        log.sync_status = "Failed"
        log.error_message = message
        if raw_payload:
            log.raw_payload = json.dumps(raw_payload, indent=4)
        log.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(title="SAP Log Update Error", message=frappe.get_traceback())


def execute_live_sap_sync(config_name):
    """Engine Universal Sinkronisasi Live dengan pengaman alur transaksi SO/PO"""
    config = frappe.get_doc("SAP Integration Config", config_name)
    target_doctype = config.erpnext_target_doctype
    
    default_company = config.get("default_company") or frappe.defaults.get_user_default("company")
    default_currency = config.get("default_currency") or "IDR"
    
    try:
        auth_data = json.loads(config.connection_and_auth)
        sap_auth = HTTPBasicAuth(auth_data.get("user"), auth_data.get("pass"))
    except Exception:
        frappe.log_error(f"Kredensial akses pada konfigurasi {config_name} salah / bukan JSON valid.")
        return
        
    last_sync = config.get("last_sync_time") or "2026-01-01T00:00:00"
    query_params = {"$filter": f"LastModifiedDateTime ge datetime'{last_sync}'"}
    if config.sap_child_array_key and "to_" in config.sap_child_array_key:
        query_params["$expand"] = config.sap_child_array_key
    
    try:
        response = requests.get(config.po_endpoint, auth=sap_auth, params=query_params, timeout=45)
        response.raise_for_status()
        sap_data = response.json()
        
        data_header_list = sap_data.get("d", {}).get("results", []) if "d" in sap_data else sap_data.get("value", [])
        
        for sap_doc in data_header_list:
            sap_id = str(sap_doc.get("SalesOrder") or sap_doc.get("PurchaseOrder") or sap_doc.get("DocNum") or "")
            if not sap_id:
                continue
                
            unique_target_field = next((r.erpnext_field for r in config.field_mappings if r.table_level == "Header" and "sap_" in r.erpnext_field), None)
            if not unique_target_field:
                unique_target_field = "sap_so_id" if target_doctype == "Sales Order" else "sap_po_id"
            
            if frappe.db.exists(target_doctype, {unique_target_field: sap_id}):
                continue
                
            try:
                frappe.db.begin()
                
                new_erp_doc = frappe.new_doc(target_doctype)
                new_erp_doc.set(unique_target_field, sap_id)
                new_erp_doc.company = default_company
                new_erp_doc.currency = default_currency
                
                # Pengamanan Master Pihak Ketiga Relasional (SO vs PO)
                sap_party = sap_doc.get("Customer") or sap_doc.get("SoldToParty") or sap_doc.get("Supplier") or sap_doc.get("CardCode")
                
                if target_doctype == "Sales Order":
                    erpnext_party = (
                        frappe.db.get_value("Customer", {"sap_customer_code": sap_party}, "name")
                        or frappe.db.get_value("Customer", {"name": sap_party}, "name")
                        or frappe.db.get_value("Customer", {"customer_name": sap_party}, "name")
                    )
                    if not erpnext_party: 
                        raise frappe.ValidationError(f"Customer SAP '{sap_party}' tidak ditemukan di ERPNext.")
                    new_erp_doc.customer = erpnext_party
                else:
                    erpnext_party = (
                        frappe.db.get_value("Supplier", {"sap_vendor_code": sap_party}, "name")
                        or frappe.db.get_value("Supplier", {"name": sap_party}, "name")
                        or frappe.db.get_value("Supplier", {"supplier_name": sap_party}, "name")
                    )
                    if not erpnext_party: 
                        raise frappe.ValidationError(f"Supplier SAP '{sap_party}' tidak ditemukan di ERPNext.")
                    new_erp_doc.supplier = erpnext_party
                
                # Pemetaan Kolom Dynamic Header
                header_rules = [r for r in config.field_mappings if r.table_level == "Header" and r.erpnext_field not in ['supplier', 'customer', 'company', 'currency']]
                for rule in header_rules:
                    raw_val = sap_doc.get(rule.sap_field)
                    new_erp_doc.set(rule.erpnext_field, sanitize_dynamic_value(raw_val, rule.data_type))
                
                if not new_erp_doc.get("transaction_date"):
                    new_erp_doc.transaction_date = frappe.utils.today()
                
                if target_doctype == "Sales Order" and not new_erp_doc.get("delivery_date"):
                    new_erp_doc.delivery_date = frappe.utils.add_days(new_erp_doc.transaction_date, 3)
                
                # Penguraian Array Baris Barang
                child_key = config.sap_child_array_key or ("DocumentLines" if "DocumentLines" in sap_doc else "to_PurchaseOrderItem")
                line_items = sap_doc.get(child_key, {})
                if isinstance(line_items, dict) and "results" in line_items:
                    line_items = line_items.get("results", [])
                
                for sap_item in line_items:
                    sap_mat = sap_item.get("Material") or sap_item.get("ItemCode")
                    erpnext_item = frappe.db.get_value("Item", {"item_code": sap_mat}, "name")
                    
                    if not erpnext_item:
                        raise frappe.ValidationError(f"Material SAP '{sap_mat}' tidak terdaftar di ERPNext.")
                    
                    item_row = {"item_code": erpnext_item}
                    item_rules = [r for r in config.field_mappings if r.table_level == "Item"]
                    for rule in item_rules:
                        raw_val = sap_item.get(rule.sap_field)
                        item_row[rule.erpnext_field] = sanitize_dynamic_value(raw_val, rule.data_type)
                    
                    if target_doctype == "Sales Order" and not item_row.get("delivery_date"):
                        item_row["delivery_date"] = new_erp_doc.delivery_date
                    if target_doctype == "Purchase Order" and not item_row.get("schedule_date"):
                        item_row["schedule_date"] = new_erp_doc.transaction_date or frappe.utils.today()
                    if not item_row.get("warehouse"):
                        item_row["warehouse"] = _get_default_warehouse(erpnext_item, default_company)
                        
                    new_erp_doc.append("items", item_row)
                
                new_erp_doc.insert(ignore_permissions=True)
                write_audit_log(sap_id, "Success", raw_payload=sap_doc)
                frappe.db.commit()
                
            except Exception as item_error:
                frappe.db.rollback()
                write_audit_log(sap_id, "Failed", message=frappe.get_traceback() or str(item_error), raw_payload=sap_doc)
        
        config.last_sync_time = frappe.utils.now_datetime().strftime("%Y-%m-%dT%H:%M:%S")
        config.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as global_error:
        frappe.log_error(title=f"SAP Sync Engine Crash [{config_name}]", message=frappe.get_traceback())

def sanitize_dynamic_value(value, data_type):
    if data_type == "Decimal":
        return parse_sap_string_decimal(value)
    elif data_type == "OData Date":
        return parse_sap_odata_date(value)
    return str(value).strip() if value else value

def write_audit_log(sap_po_id, status, message=None, raw_payload=None):
    """Menulis rekaman histori sinkronisasi terisolasi"""
    try:
        log = frappe.new_doc("SAP Integration Log")
        log.sap_po_id = sap_po_id
        log.sync_status = status
        log.execution_time = frappe.utils.now_datetime()
        log.error_message = message
        log.raw_payload = json.dumps(raw_payload, indent=4) if raw_payload else None
        log.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as log_err:
        frappe.log_error(title="Failed Writing SAP Audit Log", message=frappe.get_traceback())