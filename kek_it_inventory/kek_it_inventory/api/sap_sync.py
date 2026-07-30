# -*- coding: utf-8 -*-
import frappe
import json
import traceback
import requests
from frappe.utils import now_datetime

# ---------------------------------------------------------------------------
# PUSH endpoint (SAP pushes payload to ERPNext)
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=False)
def receive_sap_document():
    """
    Whitelisted POST endpoint for SAP to push PO/SO data.
    Identifies the correct SAP Integration Config stream by matching
    the document type to the ERPNext target doctype.
    """
    if frappe.request.method != "POST":
        frappe.throw("Only POST method is allowed", frappe.PermissionError)

    try:
        if isinstance(frappe.request.data, bytes):
            raw_payload = frappe.request.data.decode("utf-8")
        else:
            raw_payload = frappe.request.data
        payload = json.loads(raw_payload)
    except Exception as e:
        frappe.throw(f"Invalid JSON payload: {str(e)}", frappe.ValidationError)

    sap_id = payload.get("PurchaseOrder") or payload.get("SalesOrder") or payload.get("DocNum")
    if not sap_id:
        frappe.throw("Missing document identifier (PurchaseOrder, SalesOrder, or DocNum)", frappe.ValidationError)

    # Write the audit log immediately
    log = frappe.new_doc("SAP Integration Log")
    log.sap_po_id = str(sap_id)
    log.sync_status = "Failed"  # Will be updated on success
    log.execution_time = now_datetime()
    log.raw_payload = json.dumps(payload, indent=4)
    log.insert(ignore_permissions=True)
    frappe.db.commit()

    # Enqueue async processing
    frappe.enqueue(
        method="kek_it_inventory.kek_it_inventory.sap_connector.mapping_engine.execute_live_sap_sync_from_push",
        queue="default",
        job_name=f"SAP-Push-{sap_id}",
        log_name=log.name,
        raw_payload=payload
    )

    return {"status": "Queued", "log_name": log.name}


# ---------------------------------------------------------------------------
# PULL scheduler (ERPNext polls SAP periodically per config stream)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def run_all_streams():
    """Scheduled: trigger sync for all active SAP Integration Config streams."""
    from kek_it_inventory.kek_it_inventory.sap_connector.mapping_engine import execute_hourly_sync
    execute_hourly_sync()


# ---------------------------------------------------------------------------
# XLS bulk import (existing functionality retained)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# XLS bulk import (ME2N & VA05 SAP exports with Lazy Master Data & Draft PO/SO)
# ---------------------------------------------------------------------------

def normalize_sap_me2n_columns(df):
    """
    Normalizes column names in a DataFrame coming from SAP exports (ME2N, VA05, or clean schemas).
    Returns (df_normalized, doc_type):
      doc_type = "Purchase Order" or "Sales Order"
    """
    SAP_HEADER_MAP = {
        "Purchasing Document": "po_number",
        "Material": "item_code",
        "Short Text": "description",
        "Order Quantity": "qty",
        "Net Price": "rate",
        "Supplier/Supplying Plant": "supplier",
        "Supplier": "supplier",
        "Plant": "warehouse",
        "Document Date": "transaction_date",
        "Order Unit": "uom",
        "Currency": "currency",
        "Item": "item_idx",
        
        # VA05 Sales Order headers
        "Sales Document": "so_number",
        "SD Document": "so_number",
        "Sold-to Party": "customer",
        "Customer": "customer",
        "Net Value": "rate",
    }
    
    renames = {}
    for original in df.columns:
        clean_name = str(original).strip()
        if clean_name in SAP_HEADER_MAP:
            renames[original] = SAP_HEADER_MAP[clean_name]

    df_renamed = df.rename(columns=renames)
    
    # Determine doc_type: Purchase Order vs Sales Order
    if "so_number" in df_renamed.columns or "customer" in df_renamed.columns:
        doc_type = "Sales Order"
    else:
        doc_type = "Purchase Order"
        
    return df_renamed, doc_type


def ensure_supplier_or_customer(entity_name, is_supplier=True):
    """
    Lazy Master Data Creation for Supplier or Customer.
    If entity_name doesn't exist in ERPNext, creates a stub record automatically.
    """
    import pandas as pd
    if not entity_name or pd.isna(entity_name):
        entity_name = "UNKNOWN-SUPPLIER" if is_supplier else "UNKNOWN-CUSTOMER"
    
    entity_str = str(entity_name).strip()
    
    if is_supplier:
        if not frappe.db.exists("Supplier", entity_str):
            existing = frappe.db.get_value("Supplier", {"supplier_name": entity_str}, "name")
            if existing:
                return existing
            supp_group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups"
            doc = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": entity_str,
                "supplier_group": supp_group
            })
            doc.insert(ignore_permissions=True)
            return doc.name
        return entity_str
    else:
        if not frappe.db.exists("Customer", entity_str):
            existing = frappe.db.get_value("Customer", {"customer_name": entity_str}, "name")
            if existing:
                return existing
            cust_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
            doc = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": entity_str,
                "customer_group": cust_group,
                "territory": "All Territories"
            })
            doc.insert(ignore_permissions=True)
            return doc.name
        return entity_str


def ensure_item(item_code, description=None, uom=None):
    """
    Lazy Master Data Creation for Item.
    If item_code doesn't exist in ERPNext, creates a stub Item record automatically.
    """
    import pandas as pd
    if not item_code or pd.isna(item_code):
        item_code = "UNKNOWN-ITEM"
        
    item_str = str(item_code).strip()
    
    if not frappe.db.exists("Item", item_str):
        uom_str = str(uom).strip() if uom and not pd.isna(uom) else "Nos"
        if not frappe.db.exists("UOM", uom_str):
            try:
                frappe.get_doc({"doctype": "UOM", "uom_name": uom_str, "name": uom_str}).insert(ignore_permissions=True)
            except Exception:
                uom_str = "Nos"
                
        doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_str,
            "item_name": str(description).strip() if description and not pd.isna(description) else item_str,
            "item_group": "All Item Groups",
            "is_stock_item": 1,
            "stock_uom": uom_str
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    return item_str


def parse_date_string(date_val):
    """Safely parses date strings (e.g. '6/26/2026', '2026-06-26', or pandas Timestamps) to 'YYYY-MM-DD'."""
    import pandas as pd
    from frappe.utils import getdate, today
    if date_val is None or pd.isna(date_val):
        return today()
    try:
        dt = pd.to_datetime(date_val)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        try:
            return str(getdate(date_val))
        except Exception:
            return today()


def parse_float(val, default=0.0):
    """Safely converts string numbers with commas (e.g. '1,264.21') or floats to float."""
    import pandas as pd
    if val is None or pd.isna(val):
        return default
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if not val_str:
        return default
    val_clean = val_str.replace(",", "").replace(" ", "")
    try:
        return float(val_clean)
    except ValueError:
        try:
            val_eu = val_str.replace(".", "").replace(",", ".")
            return float(val_eu)
        except ValueError:
            return default


def get_default_warehouse(company=None):
    """Retrieves default non-group warehouse for PO/SO stock items matching company."""
    if not company:
        company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
    
    wh = None
    if company:
        wh = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
    if not wh:
        wh_record = frappe.db.get_value("Warehouse", {"is_group": 0}, ["name", "company"], as_dict=True)
        if wh_record:
            wh = wh_record.name
            company = wh_record.company
    return wh, company


@frappe.whitelist()
def process_sap_xls_chunked(import_job_name):
    """
    XLS Chunked Background Processor (Hybrid Method).
    Driven by the 'SAP PO Import Job' DocType.
    Supports ME2N (PO) & VA05 (SO) raw SAP Excel exports with Lazy Master Data & Draft PO creation.
    """
    import pandas as pd
    job = frappe.get_doc("SAP PO Import Job", import_job_name)
    if job.status == "Completed":
        return

    job.status = "Processing"
    job.save(ignore_permissions=True)
    frappe.db.commit()

    try:
        file_path = frappe.get_site_path(job.file_url.lstrip("/"))
        raw_df = pd.read_excel(file_path)

        df, target_doctype = normalize_sap_me2n_columns(raw_df)
        group_key = "so_number" if target_doctype == "Sales Order" else "po_number"

        if group_key not in df.columns:
            frappe.throw(f"Excel file missing identifier column '{group_key}'")

        po_groups = list(df.groupby(group_key, sort=False))

        if not job.total_rows:
            job.total_rows = len(po_groups)
            job.save(ignore_permissions=True)
            frappe.db.commit()

        if job.last_po_number:
            keys = [str(k).strip().removesuffix(".0") for k, _ in po_groups]
            if job.last_po_number in keys:
                start_idx = keys.index(job.last_po_number) + 1
                po_groups = po_groups[start_idx:]

        CHUNK_SIZE = 100
        chunk = po_groups[:CHUNK_SIZE]
        remaining = po_groups[CHUNK_SIZE:]
        default_wh, default_company = get_default_warehouse()

        for doc_number, group in chunk:
            try:
                first_row = group.iloc[0]
                doc_num_str = str(doc_number).strip().removesuffix(".0")

                if target_doctype == "Purchase Order":
                    supplier_str = ensure_supplier_or_customer(first_row.get("supplier"), is_supplier=True)
                    tx_date = parse_date_string(first_row.get("transaction_date"))
                    
                    # Idempotency check: check if PO already exists with this custom_sap_po_number
                    existing_po = frappe.db.get_value("Purchase Order", {"custom_sap_po_number": doc_num_str}, "name")
                    if not existing_po:
                        # Construct ERPNext Purchase Order Doc
                        po_items = []
                        for _, row in group.iterrows():
                            item_code_str = ensure_item(row.get("item_code"), row.get("description"), row.get("uom"))
                            qty_val = parse_float(row.get("qty"), default=1.0)
                            rate_val = parse_float(row.get("rate"), default=0.0)
                            item_wh = str(row.get("warehouse")).strip() if row.get("warehouse") and not pd.isna(row.get("warehouse")) and frappe.db.exists("Warehouse", str(row.get("warehouse")).strip()) else default_wh
                            
                            po_items.append({
                                "item_code": item_code_str,
                                "qty": qty_val,
                                "rate": rate_val,
                                "warehouse": item_wh,
                                "description": str(row.get("description", "")) if not pd.isna(row.get("description")) else ""
                            })
                            
                        po_doc = frappe.get_doc({
                            "doctype": "Purchase Order",
                            "company": default_company,
                            "supplier": supplier_str,
                            "custom_sap_po_number": doc_num_str,
                            "transaction_date": tx_date,
                            "schedule_date": tx_date,
                            "set_warehouse": default_wh,
                            "items": po_items
                        })
                        po_doc.insert(ignore_permissions=True)
                        po_name = po_doc.name
                        po_is_new = True
                    else:
                        po_name = existing_po
                        po_is_new = False

                    po_link = f'<a href="/app/purchase-order/{po_name}">{po_name}</a>'
                    if po_is_new:
                        job.add_comment("Comment", f"Successfully imported Purchase Order: {po_link}")
                    else:
                        job.add_comment("Comment", f"Purchase Order already exists: {po_link}")

                    sap_payload = {
                        "PurchaseOrder": doc_num_str,
                        "Supplier": supplier_str,
                        "to_PurchaseOrderItem": {"results": [
                            {
                                "Material": str(row.get("item_code")),
                                "OrderQuantity": parse_float(row.get("qty"), default=1.0),
                                "NetPriceAmount": parse_float(row.get("rate"), default=0.0),
                            }
                            for _, row in group.iterrows()
                        ]}
                    }
                else:
                    # Sales Order
                    customer_str = ensure_supplier_or_customer(first_row.get("customer"), is_supplier=False)
                    tx_date = parse_date_string(first_row.get("transaction_date"))
                    existing_so = frappe.db.get_value("Sales Order", {"custom_sap_so_number": doc_num_str}, "name")
                    if not existing_so:
                        so_items = []
                        for _, row in group.iterrows():
                            item_code_str = ensure_item(row.get("item_code"), row.get("description"), row.get("uom"))
                            qty_val = parse_float(row.get("qty"), default=1.0)
                            rate_val = parse_float(row.get("rate"), default=0.0)
                            so_items.append({
                                "item_code": item_code_str,
                                "qty": qty_val,
                                "rate": rate_val,
                                "description": str(row.get("description", "")) if not pd.isna(row.get("description")) else ""
                            })
                            
                        so_doc = frappe.get_doc({
                            "doctype": "Sales Order",
                            "company": default_company,
                            "customer": customer_str,
                            "custom_sap_so_number": doc_num_str,
                            "transaction_date": tx_date,
                            "delivery_date": tx_date,
                            "items": so_items
                        })
                        so_doc.insert(ignore_permissions=True)
                        so_name = so_doc.name
                        so_is_new = True
                    else:
                        so_name = existing_so
                        so_is_new = False

                    so_link = f'<a href="/app/sales-order/{so_name}">{so_name}</a>'
                    if so_is_new:
                        job.add_comment("Comment", f"Successfully imported Sales Order: {so_link}")
                    else:
                        job.add_comment("Comment", f"Sales Order already exists: {so_link}")


                    sap_payload = {
                        "SalesOrder": doc_num_str,
                        "Customer": customer_str,
                        "to_SalesOrderItem": {"results": [
                            {
                                "Material": str(row.get("item_code")),
                                "OrderQuantity": parse_float(row.get("qty"), default=1.0),
                                "NetPriceAmount": parse_float(row.get("rate"), default=0.0),
                            }
                            for _, row in group.iterrows()
                        ]}
                    }

                from kek_it_inventory.kek_it_inventory.sap_connector.mapping_engine import write_audit_log
                write_audit_log(doc_num_str, "Success", raw_payload=sap_payload)
                job.processed_rows += 1
                job.last_po_number = doc_num_str

            except Exception as row_error:
                frappe.db.rollback()
                error_msg = f"\n{target_doctype} {doc_number}: {str(row_error)}"
                job.error_log = (job.error_log or "") + error_msg
                frappe.log_error(f"SAP XLS Import Row Error: {doc_number}", str(row_error))

        job.save(ignore_permissions=True)
        frappe.db.commit()


        if remaining:
            frappe.enqueue(
                method="kek_it_inventory.kek_it_inventory.api.sap_sync.process_sap_xls_chunked",
                queue="long",
                import_job_name=import_job_name,
                timeout=3600
            )
            return

        job.status = "Completed"
        job.save(ignore_permissions=True)
        frappe.db.commit()

        # Final commit to ensure all docs are saved
        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        job.status = "Failed"
        job.error_log = (job.error_log or "") + f"\nJob-level Failure: {str(e)}\n{traceback.format_exc()}"
        job.save(ignore_permissions=True)
        frappe.db.commit()

