import frappe
from frappe.utils import add_days, today

@frappe.whitelist()
def get_failed_count():
    """Mengembalikan jumlah transaksi yang gagal untuk ditampilkan di badge desktop."""
    return frappe.db.count("KEK Inventory Transaction", {"status": "FAILED"})

def daily_payload_summary():
    """Mengirim ringkasan transaksi kemarin ke tim operasional."""
    yesterday = add_days(today(), -1)
    
    stats = frappe.db.sql("""
        SELECT status, COUNT(*) as count 
        FROM `tabKEK Inventory Transaction` 
        WHERE DATE(transaction_date) = %s 
        GROUP BY status
    """, yesterday, as_dict=True)
    
    if not stats:
        return

    message = f"Ringkasan Transaksi KEK ({yesterday}):<br><br>"
    for s in stats:
        message += f"- {s.status}: {s.count}<br>"
        
    frappe.sendmail(
        recipients=["admin@example.com"], # Sesuaikan email tujuan
        subject=f"Daily KEK Inventory Summary - {yesterday}",
        message=message
    )
