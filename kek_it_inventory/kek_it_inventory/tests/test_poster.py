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

	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.post')
	def test_post_transaction_with_real_creds(self, mock_post):
		# Mock a successful response
		mock_post.return_value.status_code = 200
		mock_post.return_value.json.return_value = {
			"status": "success",
			"idTransaksi": "SINSW-REAL-123"
		}

		# Execute
		post_transaction(self.txn.name)

		# Verify Headers in Request
		args, kwargs = mock_post.call_args
		headers = kwargs.get('headers')
		self.assertEqual(headers["X-INSW-Key"], "SECRET-INSW-KEY")
		self.assertEqual(headers["X-Unique-Key"], "SECRET-UNIQUE-KEY")

		# Verify Payload
		payload = json.loads(kwargs.get('data'))
		self.assertEqual(payload["npwp"], "012345678901234")
		self.assertEqual(payload["nib"], "NIB-123")

		# Verify Doc Update
		self.txn.reload()
		self.assertEqual(self.txn.status, "SENT")
		self.assertEqual(self.txn.insw_transaksi_id, "SINSW-REAL-123")

		# 4. Verify Ledger Entry
		ledger_entries = frappe.get_all("KEK Stock Ledger", 
			filters={"voucher_no": self.txn.erpnext_reference_name},
			fields=["qty_in", "qty_balance", "customs_item_code"]
		)
		self.assertEqual(len(ledger_entries), 1)
		self.assertEqual(ledger_entries[0].qty_in, 10)
		self.assertEqual(ledger_entries[0].qty_balance, 10)
		self.assertEqual(ledger_entries[0].customs_item_code, "ITEM001")

	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.post')
	def test_process_queue(self, mock_post):
		mock_post.return_value.status_code = 200
		mock_post.return_value.json.return_value = {"status": "success", "idTransaksi": "999"}
		
		process_queue(sync=True)
		
		self.txn.reload()
		self.assertEqual(self.txn.status, "SENT")
