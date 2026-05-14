import frappe
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from kek_it_inventory.kek_it_inventory.api.ledger import update_ledger

def run_delivery_simulation():
	print("--- MEMULAI SIMULASI DELIVERY NOTE (PENGELUARAN) ---")
	
	company = "bcmerak"
	item_code = "_Test Item"
	cost_center = "Main - Bcm"
	expense_account = "4210.000 - HPP Pembelian - Bcm"
	customer = "Grant Plastics Ltd."
	price_list = "Standard Selling"

	# 1. Langkah 1: Buat Delivery Note di ERPNext
	print("Langkah 1: Membuat Delivery Note di ERPNext (Kirim 3 Unit)...")
	
	# Manually create to avoid test helper issues
	dn = frappe.get_doc({
		"doctype": "Delivery Note",
		"company": company,
		"customer": customer,
		"posting_date": frappe.utils.today(),
		"price_list_currency": "IDR",
		"selling_price_list": price_list,
		"currency": "IDR",
		"items": [
			{
				"item_code": item_code,
				"qty": 3,
				"rate": 10000,
				"warehouse": "Finished Goods - BCM",
				"cost_center": cost_center,
				"expense_account": expense_account
			}
		]
	})
	
	dn.insert(ignore_permissions=True)
	dn.submit()
	print(f"✅ Delivery Note {dn.name} Berhasil di-Submit.")

	# 2. Langkah 2: Cek Bridge
	kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", 
		{"erpnext_reference_name": dn.name}, "name")
	
	if kek_txn_name:
		print(f"✅ Bridge Berhasil! Transaksi KEK Pengeluaran tercipta: {kek_txn_name}")
		
		# 3. Langkah 3: Simulasi Pengiriman API
		doc = frappe.get_doc("KEK Inventory Transaction", kek_txn_name)
		doc.status = "SENT"
		doc.insw_transaksi_id = "TX-OUT-SIMULASI-222"
		doc.save()
		
		# Update Ledger
		update_ledger(doc.name)
		print("✅ API Terkirim & Ledger Berhasil Dicatatkan (Pengurangan).")

		# 4. Langkah 4: Tampilkan Rekapitulasi Ledger
		print("\n--- REKAPITULASI KEK STOCK LEDGER (KRONOLOGIS) ---")
		ledger = frappe.get_all("KEK Stock Ledger", 
			filters={"customs_item_code": "KEK-SIMULASI-CODE"},
			fields=["voucher_no", "qty_in", "qty_out", "qty_balance", "creation"],
			order_by="creation asc"
		)
		
		for entry in ledger:
			flow = f"+{entry.qty_in}" if entry.qty_in > 0 else f"-{entry.qty_out}"
			print(f"Doc: {entry.voucher_no} | Mutasi: {flow} | Saldo: {entry.qty_balance}")

	else:
		print("❌ Bridge Gagal menciptakan transaksi.")

if __name__ == "__main__":
	run_delivery_simulation()
