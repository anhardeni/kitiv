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

@frappe.whitelist()
def process_sap_xls_chunked(job_name):
    """
    XLS Chunked Background Processor (Hybrid Method).
    Driven by the 'SAP PO Import Job' DocType.
    """
    import pandas as pd
    job = frappe.get_doc("SAP PO Import Job", job_name)
    if job.status == "Completed":
        return

    job.status = "Processing"
    job.save(ignore_permissions=True)
    frappe.db.commit()

    try:
        file_path = frappe.get_site_path(job.file_url.lstrip("/"))
        df = pd.read_excel(file_path)

        po_groups = list(df.groupby("po_number", sort=False))

        if not job.total_rows:
            job.total_rows = len(po_groups)
            job.save(ignore_permissions=True)
            frappe.db.commit()

        if job.last_po_number:
            keys = [str(k) for k, _ in po_groups]
            if job.last_po_number in keys:
                start_idx = keys.index(job.last_po_number) + 1
                po_groups = po_groups[start_idx:]

        CHUNK_SIZE = 100
        chunk = po_groups[:CHUNK_SIZE]
        remaining = po_groups[CHUNK_SIZE:]

        for po_number, group in chunk:
            try:
                first_row = group.iloc[0]
                sap_po = {
                    "PurchaseOrder": str(po_number),
                    "Supplier": str(first_row["supplier"]),
                    "CompanyCode": str(first_row["company"]),
                    "DocumentCurrency": str(first_row.get("currency", "IDR")),
                    "CreationDate": str(first_row.get("transaction_date", frappe.utils.today())),
                    "to_PurchaseOrderItem": {"results": [
                        {
                            "Material": str(row["item_code"]),
                            "OrderQuantity": float(row["qty"]),
                            "PurchaseOrderQuantityUnit": str(row["uom"]),
                            "NetPriceAmount": float(row["rate"]),
                            "Plant": str(row["warehouse"]),
                            "PurchaseOrderItemText": str(row.get("description", ""))
                        }
                        for _, row in group.iterrows()
                    ]}
                }

                from kek_it_inventory.kek_it_inventory.sap_connector.mapping_engine import write_audit_log
                write_audit_log(str(po_number), "Success", raw_payload=sap_po)
                job.processed_rows += 1
                job.last_po_number = str(po_number)

            except Exception as row_error:
                frappe.db.rollback()
                error_msg = f"\nPO {po_number}: {str(row_error)}"
                job.error_log = (job.error_log or "") + error_msg
                frappe.log_error(f"SAP XLS Import Row Error: {po_number}", str(row_error))

        job.save(ignore_permissions=True)
        frappe.db.commit()

        if remaining:
            frappe.enqueue(
                method="kek_it_inventory.kek_it_inventory.api.sap_sync.process_sap_xls_chunked",
                queue="long",
                job_name=job_name,
                timeout=3600
            )
            return

        job.status = "Completed"
        job.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        job.status = "Failed"
        job.error_log = (job.error_log or "") + f"\nJob-level Failure: {str(e)}\n{traceback.format_exc()}"
        job.save(ignore_permissions=True)
        frappe.db.commit()
