import frappe
import unittest
import json
from unittest.mock import patch
from kek_it_inventory.kek_it_inventory.api.poster import post_transaction, process_queue

class TestPoster(unittest.TestCase):
	def setUp(self):
		# 0. Clear previous test data to avoid leakage
		frappe.db.delete("KEK Stock Ledger", {"customs_item_code": "ITEM001"})
		
		# 1. Create/Update Company Profile
		if not frappe.db.exists("KEK Company Profile", "TEST COMPANY"):
			self.profile = frappe.get_doc({
				"doctype": "KEK Company Profile",
				"company_name": "TEST COMPANY",
				"npwp": "012345678901234",
				"nib": "NIB-123",
				"erpnext_company": "bcmerak"
			}).insert()
		else:
			self.profile = frappe.get_doc("KEK Company Profile", "TEST COMPANY")
			self.profile.nib = "NIB-123"
			self.profile.npwp = "012345678901234"
			self.profile.save()
		
		# 2. Create/Update API Credentials
		cred_name = f"KEK-CRED-TEST COMPANY-DUMMY"
		if not frappe.db.exists("KEK API Credential", cred_name):
			self.cred = frappe.get_doc({
				"doctype": "KEK API Credential",
				"company_profile": "TEST COMPANY",
				"environment": "DUMMY",
				"active": 1,
				"base_url": "https://api-dummy.sinsw.go.id",
				"x_insw_key": "SECRET-INSW-KEY",
				"x_unique_key": "SECRET-UNIQUE-KEY"
			}).insert()
		else:
			self.cred = frappe.get_doc("KEK API Credential", cred_name)
			self.cred.active = 1
			self.cred.x_insw_key = "SECRET-INSW-KEY"
			self.cred.x_unique_key = "SECRET-UNIQUE-KEY"
			self.cred.save()

		# 3. Create a Transaction
		self.txn = frappe.get_doc({
			"doctype": "KEK Inventory Transaction",
			"company_profile": "TEST COMPANY",
			"transaction_date": frappe.utils.today(),
			"transaction_type": "30",
			"status": "QUEUED",
			"items": [
				{
					"customs_item_code": "ITEM001",
					"qty": 10,
					"uom_code": "PCE"
				}
			]
		}).insert()

	def tearDown(self):
		frappe.db.rollback()

	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.get')
	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.post')
	def test_post_transaction_with_real_creds(self, mock_post, mock_get):
		# Mock Unique Key response
		mock_get.return_value.status_code = 200
		mock_get.return_value.json.return_value = {"uniqueKey": "SECRET-UNIQUE-KEY"}

		# Mock a successful post response
		success_res = {
			"status": True,
			"code": "01",
			"data": {
				"resultDataTransaksi": [{"idTransaksi": "SINSW-REAL-123"}],
				"resultBarangTransaksi": [{"idBarangTransaksi": "ITEM-INSW-ID-123", "kdBarang": "ITEM001"}]
			}
		}
		mock_post.return_value.status_code = 200
		mock_post.return_value.json.return_value = success_res
		mock_post.return_value.text = json.dumps(success_res)

		# Execute
		post_transaction(self.txn.name)

		# Verify Headers in Request
		args, kwargs = mock_post.call_args
		headers = kwargs.get('headers')
		self.assertEqual(headers["x-insw-key"], "SECRET-INSW-KEY")
		self.assertEqual(headers["x-unique-key"], "SECRET-UNIQUE-KEY")

		# Verify Payload (PER-24 Structure)
		payload = json.loads(kwargs.get('data'))
		self.assertEqual(payload["data"][0]["kdKegiatan"], "30")

		# Verify Doc Update
		self.txn.reload()
		self.assertEqual(self.txn.status, "SENT")
		self.assertEqual(self.txn.insw_transaksi_id, "SINSW-REAL-123")
		self.assertEqual(self.txn.items[0].id_barang_transaksi_insw, "ITEM-INSW-ID-123")

		# 4. Verify Ledger Entry
		ledger_entries = frappe.get_all("KEK Stock Ledger", 
			filters={"voucher_no": self.txn.erpnext_reference_name, "customs_item_code": "ITEM001"},
			fields=["qty_in", "qty_balance", "customs_item_code"]
		)
		self.assertEqual(len(ledger_entries), 1)
		self.assertEqual(ledger_entries[0].qty_in, 10)
		self.assertEqual(ledger_entries[0].qty_balance, 10)
		self.assertEqual(ledger_entries[0].customs_item_code, "ITEM001")

	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.get')
	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.post')
	def test_process_queue(self, mock_post, mock_get):
		mock_get.return_value.status_code = 200
		mock_get.return_value.json.return_value = {"uniqueKey": "SECRET-UNIQUE-KEY"}

		success_res = {
			"status": True,
			"code": "01",
			"data": {
				"resultDataTransaksi": [{"idTransaksi": "999"}],
				"resultBarangTransaksi": [{"idBarangTransaksi": "ITEM-INSW-ID-999", "kdBarang": "ITEM001"}]
			}
		}
		mock_post.return_value.status_code = 200
		mock_post.return_value.json.return_value = success_res
		mock_post.return_value.text = json.dumps(success_res)
		
		process_queue(sync=True)
		
		self.txn.reload()
		self.assertEqual(self.txn.status, "SENT")

	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.get')
	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.post')
	def test_post_stock_reconciliation_payload(self, mock_post, mock_get):
		# 1. Create a type 32 (Stock Opname) transaction
		txn32 = frappe.get_doc({
			"doctype": "KEK Inventory Transaction",
			"company_profile": "TEST COMPANY",
			"transaction_date": frappe.utils.today(),
			"transaction_type": "32",
			"status": "QUEUED",
			"items": [
				{
					"customs_item_code": "ITEM002",
					"qty": 5,
					"uom_code": "PCE"
				}
			]
		}).insert()

		# Mock Dynamic key
		mock_get.return_value.status_code = 200
		mock_get.return_value.json.return_value = {"uniqueKey": "SECRET-UNIQUE-KEY"}

		# Mock success response
		success_res = {
			"status": True,
			"code": "01",
			"data": {
				"resultDataTransaksi": [{"idTransaksi": "SINSW-OPNAME-999"}],
				"resultBarangTransaksi": [{"idBarangTransaksi": "ITEM-INSW-ID-002", "kdBarang": "ITEM002"}]
			}
		}
		mock_post.return_value.status_code = 200
		mock_post.return_value.json.return_value = success_res
		mock_post.return_value.text = json.dumps(success_res)

		# Execute
		post_transaction(txn32.name)

		# Verify
		args, kwargs = mock_post.call_args
		payload = json.loads(kwargs.get('data'))
		self.assertEqual(payload["data"][0]["kdKegiatan"], "32")
		self.assertEqual(payload["data"][0]["dokumenKegiatan"][0]["barangTransaksi"][0]["kdBarang"], "ITEM002")
		self.assertEqual(payload["data"][0]["dokumenKegiatan"][0]["barangTransaksi"][0]["jumlah"], 5)

		txn32.reload()
		self.assertEqual(txn32.status, "SENT")
		self.assertEqual(txn32.insw_transaksi_id, "SINSW-OPNAME-999")
		self.assertEqual(txn32.items[0].id_barang_transaksi_insw, "ITEM-INSW-ID-002")

		# Clean up to prevent test leakage
		frappe.db.delete("KEK Stock Ledger", {"customs_item_code": "ITEM002"})

	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.get')
	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.put')
	def test_update_customs_documents(self, mock_put, mock_get):
		# Setup transaction with insw_transaksi_id and item with id_barang_transaksi_insw
		self.txn.insw_transaksi_id = "SINSW-REAL-123"
		self.txn.items[0].id_barang_transaksi_insw = "ITEM-INSW-ID-123"
		self.txn.save()

		# Add customs doc
		frappe.get_doc({
			"doctype": "KEK Item Customs Doc",
			"parent": self.txn.items[0].name,
			"parenttype": "KEK Inventory Transaction Item",
			"parentfield": "customs_docs",
			"customs_doc_code": "0407611",
			"customs_doc_number": "NEW-123",
			"customs_doc_date": "2026-07-21"
		}).insert(ignore_permissions=True)

		# Mock Unique Key
		mock_get.return_value.status_code = 200
		mock_get.return_value.json.return_value = {"uniqueKey": "SECRET-UNIQUE-KEY"}

		# Mock success response for PUT
		success_res = {"status": True, "code": "01", "message": "Success"}
		mock_put.return_value.status_code = 200
		mock_put.return_value.json.return_value = success_res
		mock_put.return_value.text = json.dumps(success_res)

		# Execute
		from kek_it_inventory.kek_it_inventory.api.poster import update_customs_documents
		res = update_customs_documents(self.txn.name)

		# Verify PUT was called with correct payload
		self.assertEqual(res, "Success")
		args, kwargs = mock_put.call_args
		payload = json.loads(kwargs.get('data'))
		self.assertEqual(payload["idTransaksi"], "SINSW-REAL-123")
		self.assertEqual(payload["idBarangTransaksi"], "ITEM-INSW-ID-123")
		self.assertEqual(payload["kodeDokumen"], "0407611")
		self.assertEqual(payload["nomorDokumen"], "NEW-123")
		self.assertEqual(payload["tanggalDokumen"], "21-07-2026")

	def test_uniqueness_validation(self):
		# First ensure the existing one is active
		self.cred.active = 1
		self.cred.save()

		new_cred = frappe.new_doc("KEK API Credential")
		new_cred.company_profile = "TEST COMPANY"
		new_cred.environment = "REAL"
		new_cred.active = 1
		new_cred.base_url = "https://api.sinsw.go.id"
		new_cred.x_insw_key = "ANOTHER-SECRET"
		new_cred.x_unique_key = "ANOTHER-UNIQUE"

		self.assertRaises(frappe.ValidationError, new_cred.insert)

	def test_get_decrypted_keys(self):
		keys = self.cred.get_decrypted_keys()
		self.assertEqual(keys["x_insw_key"], "SECRET-INSW-KEY")
		self.assertEqual(keys["x_unique_key"], "SECRET-UNIQUE-KEY")

