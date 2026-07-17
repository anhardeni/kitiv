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

        # 2. Cari semua dokumen KEK Inventory Transaction yang baru saja dibuat
        kek_txns = frappe.get_all("KEK Inventory Transaction", filters={
            "erpnext_reference_doctype": "Purchase Receipt",
            "erpnext_reference_name": doc.name,
            "status": "QUEUED"
        }, fields=["name"])

        # 3. Post langsung transaksi-transaksi tersebut ke portal SINSW/Bea Cukai
        if kek_txns:
            for txn in kek_txns:
                post_transaction(txn.name)
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
        exists = frappe.db.get_value("KEK Inventory Transaction", {
            "erpnext_reference_doctype": "Delivery Note",
            "erpnext_reference_name": doc.name
        }, ["name", "status"], as_dict=True)
        
        if exists:
            # Jika KEK transaction sudah ada dan berstatus PENDING/QUEUED, sinkronkan item-itemnya
            if exists.status in ["PENDING", "QUEUED"]:
                kek_txn = frappe.get_doc("KEK Inventory Transaction", exists.name)
                kek_txn.set("items", [])
                
                for item in doc.items:
                    item_master = frappe.db.get_value("Item", item.item_code, ["item_name", "description"], as_dict=True) or {}
                    mapping = frappe.db.get_value("KEK Item Mapping", 
                        {"erpnext_item": item.item_code}, 
                        ["customs_item_code", "customs_item_name", "hs_code"], 
                        as_dict=1
                    )
                    if mapping:
                        customs_code = mapping.customs_item_code
                        customs_name = mapping.customs_item_name or item_master.get("item_name") or item.get("item_name")
                    else:
                        customs_code = item.item_code
                        customs_name = item_master.get("item_name") or item.get("item_name") or item.item_code

                    kek_txn.append("items", {
                        "customs_item_code": customs_code,
                        "item_name_customs": customs_name,
                        "qty": item.qty,
                        "uom_code": item.get("uom") or frappe.db.get_value("Item", item.item_code, "stock_uom"),
                        "origin_type": "TLDDP",
                        "business_flow_type": "PROCESSING"
                    })
                
                kek_txn.transaction_date = doc.posting_date or doc.transaction_date
                kek_txn.save(ignore_permissions=True)
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


def delete_delivery_note_kek(doc, method=None):
    """
    Dipanggil saat Delivery Note draft dihapus (on_trash)
    → menghapus dokumen KEK Inventory Transaction terkait jika statusnya masih PENDING/QUEUED
    """
    kek_txn = frappe.db.get_value("KEK Inventory Transaction", {
        "erpnext_reference_doctype": "Delivery Note",
        "erpnext_reference_name": doc.name
    }, ["name", "status"], as_dict=True)
    
    if kek_txn and kek_txn.status in ["PENDING", "QUEUED"]:
        frappe.delete_doc("KEK Inventory Transaction", kek_txn.name, force=True)
        frappe.msgprint(f"Transaksi KEK terkait ({kek_txn.name}) telah dihapus otomatis.")


def cancel_delivery_note_kek(doc, method=None):
    """
    Dipanggil saat Delivery Note di-cancel
    → Jika KEK Transaction pending/queued, hapus/batalkan otomatis
    → Jika sudah SENT/ACKNOWLEDGED/Validated, set status transaksi KEK ke CANCEL_PENDING dan minta batal manual
    """
    kek_txn = frappe.db.get_value("KEK Inventory Transaction", {
        "erpnext_reference_doctype": "Delivery Note",
        "erpnext_reference_name": doc.name
    }, ["name", "status"], as_dict=True)
    
    if kek_txn:
        if kek_txn.status in ["PENDING", "QUEUED"]:
            frappe.delete_doc("KEK Inventory Transaction", kek_txn.name, force=True)
            frappe.msgprint(f"Transaksi KEK terkait ({kek_txn.name}) telah dibatalkan otomatis.")
        elif kek_txn.status in ["SENT", "ACKNOWLEDGED", "Validated"]:
            frappe.db.set_value("KEK Inventory Transaction", kek_txn.name, "status", "CANCEL_PENDING")
            
            # Tambahkan comment instruksi pabean
            txn_doc = frappe.get_doc("KEK Inventory Transaction", kek_txn.name)
            comment_text = "<b>Delivery Note dibatalkan di ERPNext.</b><br>Harap segera lakukan pengajuan pembatalan resmi (Batal Aju) di portal Bea Cukai/SINSW untuk transaksi ini."
            txn_doc.add_comment("Comment", text=comment_text)
            
            frappe.msgprint(
                msg="""⚠️ <b>Perhatian:</b> Surat Jalan dibatalkan, namun dokumen pabean sudah terkirim/disetujui.<br>
                Status Transaksi KEK diubah menjadi <b>CANCEL_PENDING</b>. Harap lakukan pembatalan manual di portal Bea Cukai!""",
                title="Pembatalan Dokumen KEK"
            )


def sync_existing_kek_transaction(parent_doc, kek_txn_name):
    if not kek_txn_name:
        return
    # Update parent transaction fields
    update_fields = {
        "nomor_ppkek": parent_doc.get("nomor_ppkek") or parent_doc.get("custom_bc_registration_no"),
        "tanggal_ppkek": parent_doc.get("tanggal_ppkek") or parent_doc.get("custom_bc_registration_date")
    }
    frappe.db.set_value("KEK Inventory Transaction", kek_txn_name, update_fields)
    
    # Update KEK Item Customs Doc child rows
    bc_doc_mapping = {
        "BC23": "0407611", "PPKEK Pemasukan LDP (BC23)": "0407611",
        "BC40": "0407613", "PPKEK Pemasukan TLDDP (BC40)": "0407613",
        "BC16": "0407613", "PPKEK Pemasukan TLDDP (BC16)": "0407613",
        "BC262": "0407614", "PPKEK Pemasukan Kembali ex-Subkon (BC262)": "0407614",
        "BC30": "0407631", "PPKEK Pengeluaran LDP (BC30)": "0407631",
        "BC25": "0407632", "PPKEK Pengeluaran TLDDP (BC25)": "0407632",
        "BC27": "0407621", "PPKEK Pemasukan ex-Kawasan Berikat/TPB (BC27)": "0407621",
        "BC261": "0407633", "PPKEK Pengeluaran Sementara Subkon (BC261)": "0407633",
        "Lainnya": "040700"
    }
    
    customs_doc_no = parent_doc.get("nomor_ppkek") or parent_doc.get("custom_bc_registration_no")
    if customs_doc_no:
        doc_type_raw = parent_doc.get("custom_bc_document_type") or "Lainnya"
        if doc_type_raw.startswith("0407"):
            doc_code = doc_type_raw
        else:
            doc_code = bc_doc_mapping.get(doc_type_raw, "040700")
        doc_date = parent_doc.get("custom_bc_registration_date") or parent_doc.get("posting_date") or parent_doc.get("transaction_date")
        
        kek_txn = frappe.get_doc("KEK Inventory Transaction", kek_txn_name)
        for item_row in kek_txn.items:
            frappe.db.delete("KEK Item Customs Doc", {"parent": item_row.name})
            frappe.get_doc({
                "doctype": "KEK Item Customs Doc",
                "parent": item_row.name,
                "parenttype": "KEK Inventory Transaction Item",
                "parentfield": "customs_docs",
                "customs_doc_code": doc_code,
                "customs_doc_number": customs_doc_no,
                "customs_doc_date": doc_date
            }).insert(ignore_permissions=True)


def allow_customs_edit_on_submit():
    import frappe
    fields_to_allow = [
        "custom_bc_document_type",
        "custom_bc_registration_no",
        "custom_bc_registration_date",
        "nomor_ppkek",
        "tanggal_ppkek",
        "kek_status",
        "kek_error",
        "kek_transaction",
        "bypass_kek_validation",
        "bypass_reason"
    ]
    for dt in ["Purchase Receipt", "Delivery Note"]:
        for fn in fields_to_allow:
            if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fn}):
                frappe.db.set_value("Custom Field", {"dt": dt, "fieldname": fn}, "allow_on_submit", 1)
    frappe.db.commit()
    print("Successfully configured customs fields to be editable after submit.")


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
                from kek_it_inventory.kek_it_inventory.api.bridge import create_kek_transaction
                create_kek_transaction(parent_doc)
                kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", filters, "name")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "KEK Dynamic Creation Error")
                return f"Failed to create KEK Transaction: {str(e)}"
        elif kek_txn_name and doctype:
            # Re-sync KEK Transaction fields in case the user edited them after submit
            try:
                parent_doc = frappe.get_doc(doctype, docname)
                sync_existing_kek_transaction(parent_doc, kek_txn_name)
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "KEK Re-sync Error")
    
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
    → Set status ke PENDING untuk diinput nomor PPKEK secara manual.
    """
    try:
        meta = frappe.get_meta("Purchase Order")
        if meta.has_field("kek_status"):
            doc.db_set("kek_status", "PENDING")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Orchestration Error")


def process_subcontracting_order(doc, method=None):
    """
    Dipanggil saat Subcontracting Order submit
    → Set status ke PENDING untuk diinput nomor PPKEK secara manual.
    """
    try:
        meta = frappe.get_meta("Subcontracting Order")
        if meta.has_field("kek_status"):
            doc.db_set("kek_status", "PENDING")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Orchestration Error")


def copy_parent_kek_details(doc, method=None):
    """
    Menyalin nomor_ppkek dan tanggal_ppkek langsung dari parent document (PO/SO) ke Receipt/DN.
    """
    parent_type = None
    parent_field = None
    
    if doc.doctype == "Purchase Receipt":
        parent_type = "Purchase Order"
        parent_field = "purchase_order"
    elif doc.doctype == "Subcontracting Receipt":
        parent_type = "Subcontracting Order"
        parent_field = "subcontracting_order"
    elif doc.doctype == "Delivery Note":
        parent_type = "Sales Order"
        parent_field = "against_sales_order"
        
    if not parent_type:
        return
        
    # Ambil parent name dari item pertama yang memiliki link
    parent_name = None
    for item in doc.items:
        if item.get(parent_field):
            parent_name = item.get(parent_field)
            break
            
    if not parent_name:
        return

    # 1. Jika ada kek_transaction (terutama untuk Delivery Note draft/submit)
    if doc.get("kek_transaction"):
        kek_txn = frappe.db.get_value("KEK Inventory Transaction", doc.kek_transaction, ["nomor_ppkek", "tanggal_ppkek", "status"], as_dict=True)
        if kek_txn:
            doc.nomor_ppkek = kek_txn.nomor_ppkek
            doc.tanggal_ppkek = kek_txn.get("tanggal_ppkek")
            doc.custom_bc_registration_no = kek_txn.nomor_ppkek
            doc.custom_bc_registration_date = kek_txn.get("tanggal_ppkek")
            doc.kek_status = kek_txn.status
    # 2. Jika tidak ada kek_transaction, copy dari parent PO/SO (untuk Purchase/Subcontract Receipt)
    elif parent_type in ["Purchase Order", "Subcontracting Order"]:
        parent_kek = frappe.db.get_value(parent_type, parent_name, ["kek_status", "nomor_ppkek", "tanggal_ppkek"], as_dict=True)
        if parent_kek:
            if not doc.get("nomor_ppkek"):
                doc.nomor_ppkek = parent_kek.nomor_ppkek
                doc.tanggal_ppkek = parent_kek.get("tanggal_ppkek")
                doc.kek_status = parent_kek.kek_status
            
            if doc.get("nomor_ppkek") and not doc.get("custom_bc_registration_no"):
                doc.custom_bc_registration_no = doc.nomor_ppkek
            if doc.get("tanggal_ppkek") and not doc.get("custom_bc_registration_date"):
                doc.custom_bc_registration_date = doc.tanggal_ppkek

    # 3. Always enforce two-way sync between nomor_ppkek and custom_bc_registration fields
    if doc.get("nomor_ppkek") and not doc.get("custom_bc_registration_no"):
        doc.custom_bc_registration_no = doc.nomor_ppkek
    elif doc.get("custom_bc_registration_no") and not doc.get("nomor_ppkek"):
        doc.nomor_ppkek = doc.custom_bc_registration_no

    if doc.get("tanggal_ppkek") and not doc.get("custom_bc_registration_date"):
        doc.custom_bc_registration_date = doc.tanggal_ppkek
    elif doc.get("custom_bc_registration_date") and not doc.get("tanggal_ppkek"):
        doc.tanggal_ppkek = doc.custom_bc_registration_date



def validate_kek_submission(doc, method=None):
    """
    Memvalidasi status PPKEK sebelum receipt/Delivery Note disubmit.
    Harus berstatus 'ACKNOWLEDGED' atau 'Validated' atau jika dibypass.
    """
    parent_field = None
    if doc.doctype == "Purchase Receipt":
        parent_field = "purchase_order"
    elif doc.doctype == "Subcontracting Receipt":
        parent_field = "subcontracting_order"
    elif doc.doctype == "Delivery Note":
        parent_field = "against_sales_order"
        
    if not parent_field:
        return
        
    has_parent = any(item.get(parent_field) for item in doc.items)
    if not has_parent:
        return # Skip validation for standalone receipts/DNs

    copy_parent_kek_details(doc)

    doc_label = "Penerimaan Barang" if doc.doctype in ["Purchase Receipt", "Subcontracting Receipt"] else "Pengiriman Barang (Surat Jalan)"
    sol_label = "form penerimaan barang" if doc.doctype in ["Purchase Receipt", "Subcontracting Receipt"] else "form pengiriman barang"
    loc_label = "penerimaan" if doc.doctype in ["Purchase Receipt", "Subcontracting Receipt"] else "pengiriman"

    if doc.get("bypass_kek_validation"):
        doc.kek_status = "BYPASSED"
        if doc.get("kek_transaction"):
            frappe.db.set_value("KEK Inventory Transaction", doc.kek_transaction, {"status": "Bypassed"})
            txn_doc = frappe.get_doc("KEK Inventory Transaction", doc.kek_transaction)
            comment_text = "<b>Emergency Bypass Enabled</b><br>User: {0}<br>Reason: {1}".format(
                frappe.session.user, doc.get("bypass_reason") or "No reason provided"
            )
            txn_doc.add_comment("Comment", text=comment_text)
        return

    # 1. Untuk Delivery Note (Outbound): KEK Transaction harus ada dan valid
    if doc.doctype == "Delivery Note":
        if not doc.get("kek_transaction"):
            frappe.throw(
                msg=f"🚫 <b>Gagal Submit {doc_label}:</b><br><br>Transaksi KEK belum terbuat untuk dokumen ini.",
                title="Transaksi KEK Kosong"
            )
        kek_txn_status = frappe.db.get_value("KEK Inventory Transaction", doc.kek_transaction, "status")
        if kek_txn_status not in ["ACKNOWLEDGED", "Validated", "SENT", "BYPASSED"]:
            frappe.throw(
                msg=f"🚫 <b>Gagal Submit {doc_label}:</b><br><br>Dokumen PPKEK ({doc.kek_transaction}) belum divalidasi (Status: {kek_txn_status}).",
                title="Validasi KEK Gagal"
            )
        if not doc.nomor_ppkek:
            frappe.throw(
                msg=f"🚫 <b>Gagal Submit {doc_label}:</b><br><br>Nomor PPKEK masih kosong.",
                title="Nomor PPKEK Kosong"
            )
    # 2. Untuk Inbound (Purchase Receipt / Subcontracting Receipt): Nomor PPKEK harus terisi
    else:
        if not doc.get("nomor_ppkek"):
            frappe.throw(
                msg="""🚫 <b>Gagal Submit {0}:</b><br><br>
                Nomor PPKEK belum diisi.<br><br>
                <b>Solusi:</b> Harap masukkan <b>Nomor PPKEK</b> pada {1} sebelum disubmit.""".format(doc_label, sol_label),
                title="Nomor PPKEK Kosong"
            )

    # 3. Validasi Item & Kuantitas secara Fleksibel (Langsung terhadap Parent PO/SO)
    parent_type = None
    if doc.doctype == "Purchase Receipt":
        parent_type = "Purchase Order"
    elif doc.doctype == "Subcontracting Receipt":
        parent_type = "Subcontracting Order"
    elif doc.doctype == "Delivery Note":
        parent_type = "Sales Order"

    parent_items = {}
    total_parent_qty = 0.0
    parent_names = set(item.get(parent_field) for item in doc.items if item.get(parent_field))

    if parent_type:
        for p_name in parent_names:
            if frappe.db.exists(parent_type, p_name):
                p_doc = frappe.get_doc(parent_type, p_name)
                for p_item in p_doc.items:
                    mapping = frappe.db.get_value("KEK Item Mapping", {"erpnext_item": p_item.item_code}, "customs_item_code")
                    code = mapping or p_item.item_code
                    parent_items[code] = parent_items.get(code, 0.0) + float(p_item.qty or 0)
                    total_parent_qty += float(p_item.qty or 0)

    # B. Cek apakah seluruh item di PR/DN terdaftar di parent PO/SO
    for item in doc.items:
        mapping = frappe.db.get_value("KEK Item Mapping", {"erpnext_item": item.item_code}, "customs_item_code")
        customs_item_code = mapping or item.item_code
        if parent_type and customs_item_code not in parent_items:
            frappe.throw(
                msg=f"🚫 <b>Gagal Submit:</b> Barang <b>{item.item_code}</b> (pabean: {customs_item_code}) tidak terdaftar dalam dokumen asal ({', '.join(parent_names)}).",
                title="Item Tidak Cocok"
            )

    # C. Cek apakah total kuantitas global di PR/DN melebihi total kuantitas global di parent PO/SO
    total_doc_qty = sum(item.qty for item in doc.items)
    if parent_type and total_doc_qty > total_parent_qty:
        frappe.throw(
            msg=f"🚫 <b>Gagal Submit:</b> Total kuantitas barang yang dikirim/diterima ({total_doc_qty}) melebihi total kuantitas pada dokumen asal ({total_parent_qty}).",
            title="Total Kuantitas Melebihi Batas"
        )

    # D. Cek apakah ada perbedaan detail item/qty per baris. Jika ada, set status ke MISMATCH tapi ijinkan submit
    doc_items_qty = {}
    for item in doc.items:
        mapping = frappe.db.get_value("KEK Item Mapping", {"erpnext_item": item.item_code}, "customs_item_code")
        code = mapping or item.item_code
        doc_items_qty[code] = doc_items_qty.get(code, 0.0) + float(item.qty or 0)

    mismatch_detected = False
    if parent_type:
        for code, qty in doc_items_qty.items():
            if code not in parent_items or abs(parent_items[code] - qty) > 0.001:
                mismatch_detected = True
                break

    if mismatch_detected:
        doc.kek_status = "MISMATCH"
        if doc.get("kek_transaction"):
            try:
                kek_txn_doc = frappe.get_doc("KEK Inventory Transaction", doc.kek_transaction)
                comment_text = "<b>⚠️ Mismatch Terdeteksi</b><br>Terdapat perbedaan item/kuantitas detail antara fisik {0} barang dengan dokumen asal.".format(loc_label)
                kek_txn_doc.add_comment("Comment", text=comment_text)
            except Exception:
                pass
    else:
        doc.kek_status = "Validated"


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
def manual_validate_ppkek(doctype, docname, nomor_ppkek, tanggal_ppkek=None, kek_transaction=None):
    """
    Memvalidasi status PPKEK secara manual oleh KEK Manager.
    Mengubah status dokumen asal menjadi Validated dan KEK Transaction menjadi ACKNOWLEDGED.
    """
    if not ("KEK Manager" in frappe.get_roles() or "System Manager" in frappe.get_roles()):
        frappe.throw("Hanya user dengan role KEK Manager atau System Manager yang dapat memproses verifikasi manual.")
        
    # 1. Tentukan KEK transaction mana yang akan di-update
    if not kek_transaction:
        parent_doc = frappe.get_doc(doctype, docname)
        kek_transaction = parent_doc.get("kek_transaction")
        
        if not kek_transaction:
            # Cari yang terbaru yang statusnya QUEUED, SENT, atau FAILED
            kek_transaction = frappe.db.get_value("KEK Inventory Transaction", {
                "erpnext_reference_doctype": doctype,
                "erpnext_reference_name": docname,
                "status": ["in", ["QUEUED", "SENT", "FAILED"]]
            }, "name", order_by="creation desc")
            
    if not kek_transaction:
        if doctype not in ["Purchase Order", "Subcontracting Order"]:
            frappe.throw(f"Tidak ditemukan transaksi KEK yang aktif untuk {doctype} {docname}")
        
    # 2. Update KEK Inventory Transaction dengan nomor PPKEK & tanggal PPKEK if it exists
    if kek_transaction:
        update_fields = {
            "status": "ACKNOWLEDGED",
            "nomor_ppkek": nomor_ppkek
        }
        if tanggal_ppkek:
            update_fields["tanggal_ppkek"] = tanggal_ppkek
            
        frappe.db.set_value("KEK Inventory Transaction", kek_transaction, update_fields)
        
        # 2.5 Update child KEK Item Customs Doc table with new PPKEK details for all item rows
        # Get customs document code from parent document if available
        doc_code = "040700"
        parent_doc = frappe.get_doc(doctype, docname)
        doc_type_raw = parent_doc.get("custom_bc_document_type") or "Lainnya"
        
        bc_doc_mapping = {
            "BC23": "0407611",
            "PPKEK Pemasukan LDP (BC23)": "0407611",
            "BC40": "0407613",
            "PPKEK Pemasukan TLDDP (BC40)": "0407613",
            "BC16": "0407613",
            "PPKEK Pemasukan TLDDP (BC16)": "0407613",
            "BC262": "0407614",
            "PPKEK Pemasukan Kembali ex-Subkon (BC262)": "0407614",
            "BC30": "0407631",
            "PPKEK Pengeluaran LDP (BC30)": "0407631",
            "BC25": "0407632",
            "PPKEK Pengeluaran TLDDP (BC25)": "0407632",
            "BC27": "0407621",
            "PPKEK Pemasukan ex-Kawasan Berikat/TPB (BC27)": "0407621",
            "BC261": "0407633",
            "PPKEK Pengeluaran Sementara Subkon (BC261)": "0407633"
        }
        
        if doc_type_raw.startswith("0407"):
            doc_code = doc_type_raw
        else:
            doc_code = bc_doc_mapping.get(doc_type_raw, "040700")
            
        txn_doc = frappe.get_doc("KEK Inventory Transaction", kek_transaction)
        for item in txn_doc.items:
            customs_docs = frappe.get_all("KEK Item Customs Doc", filters={"parent": item.name}, fields=["name"])
            if customs_docs:
                for cd in customs_docs:
                    cd_update = {"customs_doc_number": nomor_ppkek}
                    if tanggal_ppkek:
                        cd_update["customs_doc_date"] = tanggal_ppkek
                    frappe.db.set_value("KEK Item Customs Doc", cd.name, cd_update)
            else:
                frappe.get_doc({
                    "doctype": "KEK Item Customs Doc",
                    "parent": item.name,
                    "parenttype": "KEK Inventory Transaction Item",
                    "parentfield": "customs_docs",
                    "customs_doc_code": doc_code,
                    "customs_doc_number": nomor_ppkek,
                    "customs_doc_date": tanggal_ppkek or parent_doc.get("posting_date") or parent_doc.get("transaction_date")
                }).insert(ignore_permissions=True)
                
        comment_text = "<b>Verifikasi Manual PPKEK</b><br>User: {0}<br>Nomor PPKEK: {1}<br>Tanggal PPKEK: {2}".format(
            frappe.session.user, nomor_ppkek, tanggal_ppkek or "-"
        )
        txn_doc.add_comment("Comment", text=comment_text)
    
    # 3. Update status, nomor PPKEK, dan tanggal PPKEK pada reference document PO/SO
    parent_update = {
        "kek_status": "Validated",
        "nomor_ppkek": nomor_ppkek
    }
    if kek_transaction:
        parent_update["kek_transaction"] = kek_transaction
        
    parent_meta = frappe.get_meta(doctype)
    if parent_meta.has_field("tanggal_ppkek") and tanggal_ppkek:
        parent_update["tanggal_ppkek"] = tanggal_ppkek
        
    frappe.db.set_value(doctype, docname, parent_update)


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


def process_stock_reconciliation(doc, method=None):
    """
    Dipanggil saat Stock Reconciliation submit
    → memicu bridge connector lalu post ke API KEK
    """
    try:
        # 1. Panggil bridge connector untuk membuat dokumen KEK Inventory Transaction
        create_kek_transaction(doc, method)

        # 2. Cari dokumen KEK Inventory Transaction yang baru saja dibuat
        kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", {
            "erpnext_reference_doctype": "Stock Reconciliation",
            "erpnext_reference_name": doc.name
        }, "name")

        # 3. Post langsung transaksi tersebut ke portal SINSW/Bea Cukai
        if kek_txn_name:
            post_transaction(kek_txn_name)
        else:
            frappe.log_error(f"KEK transaction document not found for Stock Reconciliation {doc.name}", "KEK Orchestration Error")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Orchestration Error")
        meta = frappe.get_meta("Stock Reconciliation")
        if meta.has_field("kek_status"):
            doc.db_set("kek_status", "FAILED")
        if meta.has_field("kek_error"):
            doc.db_set("kek_error", str(e))


def process_stock_entry(doc, method=None):
    """
    Dipanggil saat Stock Entry submit
    → memicu bridge connector lalu post ke API KEK
    """
    try:
        # 1. Panggil bridge connector untuk membuat dokumen KEK Inventory Transaction
        create_kek_transaction(doc, method)

        # 2. Cari dokumen KEK Inventory Transaction yang baru saja dibuat
        kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", {
            "erpnext_reference_doctype": "Stock Entry",
            "erpnext_reference_name": doc.name
        }, "name")

        # 3. Post langsung transaksi tersebut ke portal SINSW/Bea Cukai
        if kek_txn_name:
            post_transaction(kek_txn_name)
        else:
            frappe.log_error(f"KEK transaction document not found for Stock Entry {doc.name}", "KEK Orchestration Error")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "KEK Integration Orchestration Error")
        meta = frappe.get_meta("Stock Entry")
        if meta.has_field("kek_status"):
            doc.db_set("kek_status", "FAILED")
        if meta.has_field("kek_error"):
            doc.db_set("kek_error", str(e))


def diagnose_pr_doc():
    import frappe
    name = "MAT-PRE-2026-00010"
    if not frappe.db.exists("Purchase Receipt", name):
        print(f"PR {name} does not exist!")
        return
    pr = frappe.get_doc("Purchase Receipt", name)
    print("PR Name:", pr.name)
    print("PR Docstatus:", pr.docstatus)
    print("PR nomor_ppkek:", pr.get("nomor_ppkek"))
    print("PR custom_bc_registration_no:", pr.get("custom_bc_registration_no"))
    print("PR tanggal_ppkek:", pr.get("tanggal_ppkek"))
    print("PR custom_bc_registration_date:", pr.get("custom_bc_registration_date"))
    print("PR KEK Status:", pr.get("kek_status"))


def on_delivery_note_submit(doc, method=None):
    """
    Dipanggil saat Delivery Note di-submit
    → memunculkan popup berisi pintasan (shortcut) ke KEK Inventory Transaction terkait
    """
    if doc.get("kek_transaction"):
        frappe.msgprint(
            msg=f"Transaksi KEK terkait: <a href='/app/kek-inventory-transaction/{doc.kek_transaction}'><b>{doc.kek_transaction}</b></a> telah berhasil disubmit.",
            title="Transaksi KEK Terkait"
        )