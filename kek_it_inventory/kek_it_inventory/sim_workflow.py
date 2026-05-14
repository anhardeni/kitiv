import frappe
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from kek_it_inventory.kek_it_inventory.api.poster import post_transaction
import json

def run_simulation():
	print("--- MEMULAI SIMULASI WORKFLOW ---")
	
	# 1. Pastikan Profile & Credential Siap
	company = "bcmerak"
	profile_name = "SIMULASI PROFILE"
	if not frappe.db.exists("KEK Company Profile", profile_name):
		frappe.get_doc({
			"doctype": "KEK Company Profile",
			"company_name": profile_name,
			"npwp": "000011112222333",
			"nib": "NIB-SIMULASI",
			"erpnext_company": company
		}).insert()
	
	cred_name = f"KEK-CRED-{profile_name}-DUMMY"
	if not frappe.db.exists("KEK API Credential", cred_name):
		frappe.get_doc({
			"doctype": "KEK API Credential",
			"company_profile": profile_name,
			"environment": "DUMMY",
			"active": 1,
			"base_url": "https://api-simulasi.sinsw.go.id",
			"x_insw_key": "SIM-KEY",
			"x_unique_key": "SIM-UNIQ"
		}).insert()

	# 2. Setup Item Mapping
	item_code = "_Test Item" # Item standar testing ERPNext
	if not frappe.db.exists("KEK Item Mapping", {"erpnext_item": item_code}):
		frappe.get_doc({
			"doctype": "KEK Item Mapping",
			"erpnext_item": item_code,
			"customs_item_code": "KEK-SIMULASI-CODE",
			"customs_item_name": "Barang Simulasi PER-24"
		}).insert()

	# 3. Langkah 1: Buat Purchase Receipt di ERPNext
	print("Langkah 1: Membuat Purchase Receipt di ERPNext...")
	pr = make_purchase_receipt(
		company=company,
		qty=10,
		item_code=item_code,
		warehouse="Finished Goods - BCM" # Pastikan warehouse ini ada atau sesuaikan
	)
	pr.submit()
	print(f"✅ Purchase Receipt {pr.name} Berhasil di-Submit.")

	# 4. Langkah 2: Cek apakah Bridge Otomatis membuat Transaksi KEK
	print("Langkah 2: Mengecek Jembatan (Bridge) Otomatis...")
	kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", 
		{"erpnext_reference_name": pr.name}, "name")
	
	if kek_txn_name:
		print(f"✅ Bridge Berhasil! Transaksi KEK tercipta: {kek_txn_name}")
		
		# 5. Langkah 3: Simulasi Pengiriman API (Status SENT)
		print("Langkah 3: Simulasi Pengiriman API SINSW...")
		# Kita gunakan patch/mock secara manual atau panggil langsung dengan mock response
		# Untuk simulasi ini, kita paksa status ke SENT untuk memicu ledger
		doc = frappe.get_doc("KEK Inventory Transaction", kek_txn_name)
		doc.status = "SENT"
		doc.insw_transaksi_id = "TX-SIMULASI-999"
		doc.save()
		
		# Panggil update_ledger secara manual untuk simulasi ini
		from kek_it_inventory.kek_it_inventory.api.ledger import update_ledger
		update_ledger(doc.name)
		print("✅ API Terkirim & Ledger Berhasil Dicatat.")

		# 6. Langkah 4: Tampilkan Hasil Ledger
		print("\n--- HASIL AKHIR DI KEK STOCK LEDGER ---")
		ledger = frappe.get_all("KEK Stock Ledger", 
			filters={"voucher_no": pr.name},
			fields=["customs_item_code", "qty_in", "qty_balance", "posting_datetime"]
		)
		for entry in ledger:
			print(f"Item: {entry.customs_item_code} | Masuk: {entry.qty_in} | Saldo Akhir: {entry.qty_balance}")

	else:
		print("❌ Bridge Gagal menciptakan transaksi.")

if __name__ == "__main__":
	run_simulation()
