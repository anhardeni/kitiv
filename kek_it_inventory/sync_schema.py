import frappe

def sync_schema():
    print("Mulai sinkronisasi skema DocType...")
    
    frappe.reload_doc('kek_it_inventory', 'doctype', 'kek_inventory_transaction', force=True)
    print("1. KEK Inventory Transaction tersinkronisasi.")
    
    frappe.reload_doc('kek_it_inventory', 'doctype', 'kek_inventory_transaction_item', force=True)
    print("2. KEK Inventory Transaction Item tersinkronisasi.")
    
    frappe.reload_doc('kek_it_inventory', 'doctype', 'kek_item_customs_doc', force=True)
    print("3. KEK Item Customs Doc tersinkronisasi.")
    
    frappe.reload_doc('kek_it_inventory', 'doctype', 'kek_item_tolerance', force=True)
    print("4. KEK Item Tolerance tersinkronisasi.")
    
    frappe.db.commit()
    print("Sinkronisasi selesai dan disimpan.")
