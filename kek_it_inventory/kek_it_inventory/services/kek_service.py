# kek_it_inventory/services/kek_service.py

import frappe
from kek_it_inventory.kek_it_inventory.api.bridge import create_kek_transaction
from kek_it_inventory.kek_it_inventory.api.poster import post_transaction

def process_purchase_receipt(doc, method=None):
    """
    Dipanggil saat Purchase Receipt submit
    → memicu bridge connector lalu post ke API KEK
    """
    try:
        if doc.get("bypass_kek_validation"):
            doc.db_set("kek_status", "BYPASSED")
            create_kek_transaction(doc, method)
            kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", {
                "erpnext_reference_doctype": "Purchase Receipt",
                "erpnext_reference_name": doc.name
            }, "name")
            if kek_txn_name:
                frappe.db.set_value("KEK Inventory Transaction", kek_txn_name, "status", "Bypassed")
                txn_doc = frappe.get_doc("KEK Inventory Transaction", kek_txn_name)
                comment_text = "<b>Emergency Bypass Enabled</b><br>User: {0}<br>Reason: {1}".format(
                    frappe.session.user, doc.get("bypass_reason") or "No reason provided"
                )
                txn_doc.add_comment("Comment", text=comment_text)
            return

        # 1. Panggil bridge connector untuk membuat dokumen KEK Inventory Transaction
        create_kek_transaction(doc, method)

        # 2. Cari dokumen KEK Inventory Transaction yang baru saja dibuat
        kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", {
            "erpnext_reference_doctype": "Purchase Receipt",
            "erpnext_reference_name": doc.name
        }, "name")

        # 3. Post langsung transaksi tersebut ke portal SINSW/Bea Cukai
        if kek_txn_name:
            post_transaction(kek_txn_name)
        else:
            frappe.log_error(f"KEK transaction document not found for Purchase Receipt {doc.name}", "KEK Orchestration Error")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Orchestration Error")
        # Check if fields exist to avoid DB column errors
        meta = frappe.get_meta("Purchase Receipt")
        if meta.has_field("kek_status"):
            doc.db_set("kek_status", "FAILED")
        if meta.has_field("kek_error"):
            doc.db_set("kek_error", str(e))


def process_delivery_note(doc, method=None):
    """
    Dipanggil saat Delivery Note draft disimpan
    → memicu bridge connector lalu post ke API KEK
    """
    try:
        # Cek duplikat transaksi agar tidak terbuat berkali-kali saat save draft
        exists = frappe.db.exists("KEK Inventory Transaction", {
            "erpnext_reference_doctype": "Delivery Note",
            "erpnext_reference_name": doc.name
        })
        if exists:
            return

        # 1. Panggil bridge connector untuk membuat dokumen KEK Inventory Transaction
        create_kek_transaction(doc, method)

        # 2. Cari dokumen KEK Inventory Transaction yang baru saja dibuat
        kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", {
            "erpnext_reference_doctype": "Delivery Note",
            "erpnext_reference_name": doc.name
        }, "name")

        # 3. Post langsung transaksi tersebut ke portal SINSW/Bea Cukai
        if kek_txn_name:
            post_transaction(kek_txn_name)
        else:
            frappe.log_error(f"KEK transaction document not found for Delivery Note {doc.name}", "KEK Orchestration Error")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Orchestration Error")
        meta = frappe.get_meta("Delivery Note")
        if meta.has_field("kek_status"):
            doc.db_set("kek_status", "FAILED")
        if meta.has_field("kek_error"):
            doc.db_set("kek_error", str(e))


@frappe.whitelist()
def retry_kek(docname, doctype=None):
    """
    Retry manual dari UI (baik dari ERPNext DocType maupun KEK Inventory Transaction)
    """
    # 1. Jika docname adalah KEK Inventory Transaction sendiri
    if frappe.db.exists("KEK Inventory Transaction", docname):
        kek_txn_name = docname
    else:
        # 2. Cari berdasarkan reference name
        filters = {"erpnext_reference_name": docname}
        if doctype:
            filters["erpnext_reference_doctype"] = doctype
        kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", filters, "name")
        
        # 3. JIKA BELUM ADA transaksi KEK-nya, buat baru secara dinamis!
        if not kek_txn_name and doctype:
            try:
                parent_doc = frappe.get_doc(doctype, docname)
                create_kek_transaction(parent_doc)
                # Cari lagi setelah dibuat
                kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", filters, "name")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "KEK Dynamic Creation Error")
                return f"Failed to create KEK Transaction: {str(e)}"
    
    if kek_txn_name:
        post_transaction(kek_txn_name)
        return "Retry sent"
    else:
        return "KEK Transaction not found and could not be created."


@frappe.whitelist()
def validate_only(docname, doctype=None):
    """
    Validasi data sebelum kirim
    """
    if frappe.db.exists("KEK Inventory Transaction", docname):
        kek_txn_name = docname
    else:
        filters = {"erpnext_reference_name": docname}
        if doctype:
            filters["erpnext_reference_doctype"] = doctype
        kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", filters, "name")
        
    if not kek_txn_name:
        return "KEK Transaction not found"
        
    txn = frappe.get_doc("KEK Inventory Transaction", kek_txn_name)
    if not txn.items:
        return "Error: Transaksi tidak memiliki baris barang."
        
    for item in txn.items:
        if not item.customs_item_code:
            return f"Error: Barang internal {item.customs_item_code} belum memiliki pemetaan pabean."
            
    return "Validation OK"


def process_purchase_order(doc, method=None):
    """
    Dipanggil saat Purchase Order submit
    → memicu bridge connector lalu post ke API KEK
    """
    try:
        create_kek_transaction(doc, method)
        kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", {
            "erpnext_reference_doctype": "Purchase Order",
            "erpnext_reference_name": doc.name
        }, "name")
        if kek_txn_name:
            post_transaction(kek_txn_name)
        else:
            frappe.log_error(f"KEK transaction document not found for Purchase Order {doc.name}", "KEK Orchestration Error")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Orchestration Error")
        meta = frappe.get_meta("Purchase Order")
        if meta.has_field("kek_status"):
            doc.db_set("kek_status", "FAILED")
        if meta.has_field("kek_error"):
            doc.db_set("kek_error", str(e))


def process_subcontracting_order(doc, method=None):
    """
    Dipanggil saat Subcontracting Order submit
    → memicu bridge connector lalu post ke API KEK
    """
    try:
        create_kek_transaction(doc, method)
        kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", {
            "erpnext_reference_doctype": "Subcontracting Order",
            "erpnext_reference_name": doc.name
        }, "name")
        if kek_txn_name:
            post_transaction(kek_txn_name)
        else:
            frappe.log_error(f"KEK transaction document not found for Subcontracting Order {doc.name}", "KEK Orchestration Error")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Orchestration Error")
        meta = frappe.get_meta("Subcontracting Order")
        if meta.has_field("kek_status"):
            doc.db_set("kek_status", "FAILED")
        if meta.has_field("kek_error"):
            doc.db_set("kek_error", str(e))


def copy_parent_kek_details(doc, method=None):
    """
    Menyalin nomor_ppkek dan kek_status dari PO/SO asal ke Receipt.
    """
    parent_type = None
    parent_field = None
    
    if doc.doctype == "Purchase Receipt":
        parent_type = "Purchase Order"
        parent_field = "purchase_order"
    elif doc.doctype == "Subcontracting Receipt":
        parent_type = "Subcontracting Order"
        parent_field = "subcontracting_order"
        
    if not parent_type:
        return
        
    # Ambil parent name dari item pertama yang memiliki link
    parent_name = None
    for item in doc.items:
        if item.get(parent_field):
            parent_name = item.get(parent_field)
            break
            
    if parent_name:
        parent_kek = frappe.db.get_value(parent_type, parent_name, ["kek_status", "nomor_ppkek", "kek_transaction"], as_dict=True)
        if parent_kek:
            doc.kek_status = parent_kek.kek_status
            doc.nomor_ppkek = parent_kek.nomor_ppkek
            doc.kek_transaction = parent_kek.kek_transaction


def validate_kek_submission(doc, method=None):
    """
    Memvalidasi status PPKEK sebelum receipt disubmit.
    Harus berstatus 'ACKNOWLEDGED' atau 'Validated' atau jika dibypass.
    """
    parent_field = "purchase_order" if doc.doctype == "Purchase Receipt" else "subcontracting_order"
    has_parent = any(item.get(parent_field) for item in doc.items)
    
    if not has_parent:
        return # Skip validation for standalone receipts

    copy_parent_kek_details(doc)

    if doc.get("bypass_kek_validation"):
        doc.kek_status = "BYPASSED"
        if doc.get("kek_transaction"):
            frappe.db.set_value("KEK Inventory Transaction", doc.kek_transaction, {
                "status": "Bypassed"
            })
            txn_doc = frappe.get_doc("KEK Inventory Transaction", doc.kek_transaction)
            comment_text = "<b>Emergency Bypass Enabled</b><br>User: {0}<br>Reason: {1}".format(
                frappe.session.user, doc.get("bypass_reason") or "No reason provided"
            )
            txn_doc.add_comment("Comment", text=comment_text)
        return


    if doc.kek_status not in ["ACKNOWLEDGED", "Validated", "BYPASSED"]:

        frappe.throw(
            msg="""🚫 <b>Gagal Submit Penerimaan Barang:</b><br><br>
            Dokumen PPKEK untuk transaksi asal belum divalidasi (Status KEK saat ini: <b>{0}</b>).<br><br>
            <b>Solusi:</b><br>
            1. Harap hubungi staf pabean untuk memproses dokumen PPKEK di Dashboard Monitoring.<br>
            2. Jika portal INSW sedang gangguan, hubungi <b>KEK Manager</b> untuk melakukan <i>Emergency Bypass</i>.""".format(doc.kek_status or "BELUM DIPROSES"),
            title="Validasi KEK Gagal"
        )


def check_for_mismatch(kek_txn_name):
    """
    Membandingkan item & qty di KEK Inventory Transaction dengan source ERPNext document.
    Jika ada perbedaan, set KEK status reference document ke 'MISMATCH' dan KEK Transaction status ke 'FAILED'.
    """
    try:
        kek_txn = frappe.get_doc("KEK Inventory Transaction", kek_txn_name)
        ref_doctype = kek_txn.erpnext_reference_doctype
        ref_name = kek_txn.erpnext_reference_name
        
        if not ref_doctype or not ref_name:
            return False
            
        if not frappe.db.exists(ref_doctype, ref_name):
            return False
            
        ref_doc = frappe.get_doc(ref_doctype, ref_name)
        
        # Qty per item di ERPNext
        ref_items = {}
        for item in ref_doc.get("items") or []:
            code = item.item_code
            ref_items[code] = ref_items.get(code, 0.0) + float(item.qty or 0)
            
        # Qty per item di KEK Transaction
        txn_items = {}
        for item in kek_txn.items:
            code = item.customs_item_code
            txn_items[code] = txn_items.get(code, 0.0) + float(item.qty or 0)
            
        # Perbandingan
        mismatch_detected = False
        for code, qty in ref_items.items():
            if code not in txn_items:
                mismatch_detected = True
                break
            if abs(txn_items[code] - qty) > 0.001:
                mismatch_detected = True
                break
                
        if not mismatch_detected:
            for code in txn_items:
                if code not in ref_items:
                    mismatch_detected = True
                    break
                    
        if mismatch_detected:
            # Set status ke FAILED / MISMATCH
            kek_txn.db_set("status", "FAILED")
            ref_doc.db_set("kek_status", "MISMATCH")
            
            # Log audit trail comment
            comment_text = "<b>⚠️ Mismatch Detected</b><br>Terdapat perbedaan kuantitas/item antara ERPNext document dengan pabean/customs record."
            kek_txn.add_comment("Comment", text=comment_text)
            
            # Trigger notification / log
            frappe.log_error(message=comment_text, title="KEK Mismatch Notification")
            return True
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Mismatch Detection Error")
        
    return False


def run_mismatch_check_job():
    """
    Job periodik untuk mengecek seluruh transaksi KEK 30 hari terakhir.
    """
    txns = frappe.get_all("KEK Inventory Transaction", filters={
        "creation": (">", frappe.utils.add_days(frappe.utils.nowdate(), -30))
    }, fields=["name"])
    
    mismatch_count = 0
    for txn in txns:
        if check_for_mismatch(txn.name):
            mismatch_count += 1
            
    return mismatch_count


@frappe.whitelist()
def manual_validate_ppkek(doctype, docname, nomor_ppkek):
    """
    Memvalidasi status PPKEK secara manual oleh KEK Manager.
    Mengubah status dokumen asal menjadi Validated dan KEK Transaction menjadi ACKNOWLEDGED.
    """
    if not ("KEK Manager" in frappe.get_roles() or "System Manager" in frappe.get_roles()):
        frappe.throw("Hanya user dengan role KEK Manager atau System Manager yang dapat memproses verifikasi manual.")
        
    doc = frappe.get_doc(doctype, docname)
    
    frappe.db.set_value(doctype, docname, {
        "kek_status": "Validated",
        "nomor_ppkek": nomor_ppkek
    })
    
    if doc.get("kek_transaction"):
        frappe.db.set_value("KEK Inventory Transaction", doc.kek_transaction, {
            "status": "ACKNOWLEDGED"
        })
        
        txn_doc = frappe.get_doc("KEK Inventory Transaction", doc.kek_transaction)
        comment_text = "<b>Verifikasi Manual PPKEK</b><br>User: {0}<br>Nomor PPKEK: {1}".format(
            frappe.session.user, nomor_ppkek
        )
        txn_doc.add_comment("Comment", text=comment_text)


@frappe.whitelist()
def download_customs_xls(doctype, docname):
    """
    Generate XLS file containing item details structured for Bea Cukai KEK/CEISA upload.
    """
    from frappe.utils.xlsxutils import make_xlsx
    
    doc = frappe.get_doc(doctype, docname)
    
    # Header format based on CEISA / Bea Cukai standard template
    data = [
        ["No", "Kode Barang", "Nama Barang", "Kuantitas", "Satuan", "Nilai Barang (IDR)", "Kategori Barang"]
    ]
    
    for idx, item in enumerate(doc.get("items") or [], start=1):
        customs_uom = item.get("uom_code") or item.get("uom")
        data.append([
            idx,
            item.get("item_code"),
            item.get("item_name") or item.get("item_code"),
            item.get("qty"),
            customs_uom,
            item.get("amount") or (float(item.get("qty") or 0) * float(item.get("rate") or 0)),
            item.get("category_code") or "1"
        ])
        
    xlsx_file = make_xlsx(data, "Items")
    
    frappe.response['filename'] = f"KEK_Items_{docname}.xlsx"
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'