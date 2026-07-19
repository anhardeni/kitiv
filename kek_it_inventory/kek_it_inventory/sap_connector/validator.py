# -*- coding: utf-8 -*-
import frappe
import json

SAP_HEURISTIC_MAP = {
    "header": {
        "purchaseorder": {"target": "sap_po_id", "type": "String"},
        "salesorder": {"target": "sap_so_id", "type": "String"},
        "docnum": {"target": "sap_doc_id", "type": "String"},
        "supplier": {"target": "supplier", "type": "String"},
        "cardcode": {"target": "customer", "type": "String"},
        "soldtoparty": {"target": "customer", "type": "String"},
        "documentdate": {"target": "transaction_date", "type": "OData Date"},
        "docdate": {"target": "transaction_date", "type": "String"},
    },
    "item": {
        "material": {"target": "item_code", "type": "String"},
        "itemcode": {"target": "item_code", "type": "String"},
        "orderquantity": {"target": "qty", "type": "Decimal"},
        "requestedquantity": {"target": "qty", "type": "Decimal"},
        "quantity": {"target": "qty", "type": "Decimal"},
        "netpriceamount": {"target": "rate", "type": "Decimal"},
        "netamount": {"target": "rate", "type": "Decimal"},
        "price": {"target": "rate", "type": "Decimal"},
    }
}

@frappe.whitelist()
def run_automated_mapping_check(payload):
    """Sandbox untuk pengujian kegagalan parsing skema JSON mentah"""
    report = []
    status = "Success"
    try:
        parsed_json = json.loads(payload)
        report.append("<li style='color: green;'><b>[PASS]</b> Struktur penulisan format JSON valid.</li>")
        
        data_header = parsed_json.get("d", {}) if "d" in parsed_json else parsed_json
        if any(k in data_header for k in ["DocNum", "PurchaseOrder", "SalesOrder"]):
            report.append("<li style='color: green;'><b>[PASS]</b> Struktur penanda dokumen SAP dikenali.</li>")
        else:
            report.append("<li style='color: orange;'><b>[WARN]</b> Kunci identitas data utama SAP tidak ditemukan.</li>")
    except Exception as e:
        status = "Failed"
        report.append(f"<li style='color: red;'><b>[CRASH]</b> Skrip JSON rusak total: {str(e)}</li>")
    finally:
        frappe.db.rollback()

    html_report = f"<div style='border: 1px solid #d1d8dd; padding: 12px;'><ul>{''.join(report)}</ul></div>"
    return {"status": status, "html_report": html_report}

@frappe.whitelist()
def auto_repair_sap_mappings(doc_name, payload):
    """Membaca payload sampel untuk melakukan perbaikan otomatis pada tabel anak"""
    try:
        parsed_json = json.loads(payload)
    except Exception as e:
        frappe.throw(f"Gagal membaca payload, format JSON rusak: {str(e)}")

    config_doc = frappe.get_doc("SAP Integration Config", doc_name)
    data_header = parsed_json.get("d", {}) if "d" in parsed_json else parsed_json
    
    existing_maps = {(r.sap_field, r.table_level): r for r in config_doc.field_mappings}
    new_mappings = []

    for sap_key in data_header.keys():
        if sap_key in ["__metadata", "to_PurchaseOrderItem", "to_SalesOrderItem", "DocumentLines", "odata.metadata"]:
            continue
        if (sap_key, "Header") in existing_maps:
            new_mappings.append(existing_maps[(sap_key, "Header")])
            continue
            
        match = SAP_HEURISTIC_MAP["header"].get(sap_key.lower().strip(), {"target": "", "type": "String"})
        new_mappings.append({
            "sap_field": sap_key, "erpnext_field": match["target"], "table_level": "Header", "data_type": match["type"]
        })

    child_key = config_doc.sap_child_array_key or ("DocumentLines" if "DocumentLines" in data_header else "to_PurchaseOrderItem")
    line_items = data_header.get(child_key, {})
    if isinstance(line_items, dict) and "results" in line_items:
        line_items = line_items.get("results", [])

    if line_items and isinstance(line_items, list):
        sample_item = line_items[0]
        for sap_key in sample_item.keys():
            if (sap_key, "Item") in existing_maps:
                new_mappings.append(existing_maps[(sap_key, "Item")])
                continue
                
            match = SAP_HEURISTIC_MAP["item"].get(sap_key.lower().strip(), {"target": "", "type": "String"})
            new_mappings.append({
                "sap_field": sap_key, "erpnext_field": match["target"], "table_level": "Item", "data_type": match["type"]
            })

    config_doc.set("field_mappings", [])
    for row in new_mappings:
        config_doc.append("field_mappings", row)
        
    config_doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "Success", "message": "Konfigurasi kolom pemetaan berhasil direparasi otomatis."}