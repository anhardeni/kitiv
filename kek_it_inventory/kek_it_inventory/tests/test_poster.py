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
				"resultDataTransaksi": [{"idTransaksi": "SINSW-REAL-123"}]
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
				"resultDataTransaksi": [{"idTransaksi": "999"}]
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
				"resultDataTransaksi": [{"idTransaksi": "SINSW-OPNAME-999"}]
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

		# Clean up to prevent test leakage
		frappe.db.delete("KEK Stock Ledger", {"customs_item_code": "ITEM002"})
