# kek_it_inventory/services/kek_service.py

import frappe

from kek_it_inventory.mapping.column_mapping import map_pr
from kek_it_inventory.validation.verify_api import validate_payload
from kek_it_inventory.api.append_api import send_data


def process_purchase_receipt(doc, method=None):
    """
    Dipanggil saat Purchase Receipt submit
    → kirim KEK Pemasukan (kode 30)
    """

    try:
        # 1. Mapping ERPNext → KEK
        payload = map_pr(doc)

        # 2. Validasi sebelum kirim
        validate_payload(payload)

        # 3. Kirim ke API KEK
        response = send_data(payload)

        # 4. Simpan hasil ke ERPNext
        update_kek_result(doc, response)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Error")
        doc.db_set("kek_status", "Failed")
        doc.db_set("kek_error", str(e))


def update_kek_result(doc, response):
    """
    Simpan hasil response KEK ke document ERPNext
    """

    if not response:
        doc.db_set("kek_status", "Failed")
        doc.db_set("kek_error", "No response from KEK")
        return

    if response.get("status") is True:
        data = response.get("data", {})

        doc.db_set("kek_status", "Sent")
        doc.db_set("kek_id_transaksi", data.get("idTransaksi"))
        doc.db_set("kek_response", frappe.as_json(response))

    else:
        doc.db_set("kek_status", "Failed")
        doc.db_set("kek_error", response.get("message"))
        doc.db_set("kek_response", frappe.as_json(response))


def retry_kek(docname):
    """
    Retry manual dari UI
    """

    doc = frappe.get_doc("Purchase Receipt", docname)

    process_purchase_receipt(doc)
    return "Retry sent"


def validate_only(docname):
    """
    Validasi tanpa kirim API (buat tombol UI)
    """

    doc = frappe.get_doc("Purchase Receipt", docname)

    payload = map_pr(doc)
    validate_payload(payload)

    return "Validation OK"