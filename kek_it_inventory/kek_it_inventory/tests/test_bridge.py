import frappe
import unittest
from unittest.mock import patch
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestBridge(unittest.TestCase):
	def setUp(self):
		# Create a company profile for 'bcmerak'
		if not frappe.db.exists("KEK Company Profile", "BC MERAK PROFILE"):
			self.profile = frappe.get_doc({
				"doctype": "KEK Company Profile",
				"company_name": "BC MERAK PROFILE",
				"npwp": "012345678901234",
				"erpnext_company": "bcmerak"
			}).insert()
		
		# Ensure Unit 'Nos' exists for testing
		if not frappe.db.exists("KEK Ref Unit", "Nos"):
			frappe.get_doc({
				"doctype": "KEK Ref Unit",
				"code": "Nos",
				"description": "Numbers"
			}).insert()
		
		# Create a warehouse for 'bcmerak' if not exists
		if not frappe.db.exists("Warehouse", "Test KEK Warehouse - BCM"):
			frappe.get_doc({
				"doctype": "Warehouse",
				"warehouse_name": "Test KEK Warehouse",
				"company": "bcmerak"
			}).insert()

		# Ensure Currency Exchange for INR to IDR exists to avoid 'Exchange Rate is mandatory' error
		if not frappe.db.exists("Currency Exchange", {"from_currency": "INR", "to_currency": "IDR"}):
			frappe.get_doc({
				"doctype": "Currency Exchange",
				"from_currency": "INR",
				"to_currency": "IDR",
				"exchange_rate": 185.0, # Dummy rate
				"date": frappe.utils.today()
			}).insert()

	def tearDown(self):
		frappe.db.rollback()

	def test_purchase_receipt_bridge_with_mapping(self):
		# 1. Create a Mapping for a specific item (Ensure it's what we expect)
		test_item = "_Test Item" # Standard ERPNext test item
		frappe.db.delete("KEK Item Mapping", {"erpnext_item": test_item})
		frappe.get_doc({
			"doctype": "KEK Item Mapping",
			"erpnext_item": test_item,
			"customs_item_code": "CUSTOMS-CODE-ABC",
			"customs_item_name": "Sharp Customs Name"
		}).insert()

		# 2. Create and Submit a Purchase Receipt
		pr = make_purchase_receipt(
			company="bcmerak", 
			qty=5, 
			item_code=test_item,
			warehouse="Test KEK Warehouse - BCM"
		)
		pr.submit()

		# 3. Verify KEK Transaction used the mapped code
		kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", 
			{"erpnext_reference_name": pr.name}, "name")
		
		doc = frappe.get_doc("KEK Inventory Transaction", kek_txn_name)
		self.assertEqual(doc.items[0].customs_item_code, "CUSTOMS-CODE-ABC")
		# self.assertEqual(doc.items[0].customs_item_name, "Sharp Customs Name") # Assuming field exists

	@patch('kek_it_inventory.kek_it_inventory.services.kek_service.post_transaction')
	def test_purchase_order_trigger(self, mock_post):
		# 1. Create and submit Purchase Order
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"company": "bcmerak",
			"supplier": "_Test Supplier",
			"transaction_date": frappe.utils.today(),
			"schedule_date": frappe.utils.today(),
			"items": [{
				"item_code": "_Test Item",
				"qty": 5,
				"uom": "Nos",
				"rate": 100,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		po.insert()
		po.submit()

		# 2. Verify KEK Transaction was created
		kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", 
			{"erpnext_reference_name": po.name, "erpnext_reference_doctype": "Purchase Order"}, "name")
		self.assertTrue(kek_txn_name)
		
		# 3. Verify fields on the Purchase Order itself
		po.reload()
		self.assertEqual(po.kek_status, "PENDING")
		self.assertEqual(po.kek_transaction, kek_txn_name)

	@patch('kek_it_inventory.kek_it_inventory.services.kek_service.post_transaction')
	def test_delivery_note_draft_trigger(self, mock_post):
		# 1. Create a draft Delivery Note (saved, not submitted)
		dn = frappe.get_doc({
			"doctype": "Delivery Note",
			"company": "bcmerak",
			"customer": "_Test Customer",
			"items": [{
				"item_code": "_Test Item",
				"qty": 3,
				"uom": "Nos",
				"rate": 120,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		dn.insert()

		# 2. Verify KEK Transaction was created on draft save
		kek_txn_name = frappe.db.get_value("KEK Inventory Transaction", 
			{"erpnext_reference_name": dn.name, "erpnext_reference_doctype": "Delivery Note"}, "name")
		self.assertTrue(kek_txn_name)
		
		# 3. Verify fields on the Delivery Note itself
		dn.reload()
		self.assertEqual(dn.kek_status, "QUEUED")
		self.assertEqual(dn.kek_transaction, kek_txn_name)
		
		# 4. Save again (update draft) and check it doesn't create duplicate
		dn.save()
		txn_count = frappe.db.count("KEK Inventory Transaction", {
			"erpnext_reference_name": dn.name, "erpnext_reference_doctype": "Delivery Note"
		})
		self.assertEqual(txn_count, 1)

	@patch('kek_it_inventory.kek_it_inventory.services.kek_service.post_transaction')
	def test_purchase_receipt_enforcement_and_copy(self, mock_post):
		# 1. Create and submit Purchase Order (default KEK Status is PENDING)
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"company": "bcmerak",
			"supplier": "_Test Supplier",
			"transaction_date": frappe.utils.today(),
			"schedule_date": frappe.utils.today(),
			"items": [{
				"item_code": "_Test Item",
				"qty": 5,
				"uom": "Nos",
				"rate": 100,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		po.insert()
		po.submit()
		po.reload()

		# 2. Try to create and submit Purchase Receipt referencing this PO
		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"company": "bcmerak",
			"supplier": "_Test Supplier",
			"items": [{
				"item_code": "_Test Item",
				"qty": 5,
				"uom": "Nos",
				"rate": 100,
				"purchase_order": po.name,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		pr.insert()
		
		# Verify KEK fields are copied on save/validate
		self.assertEqual(pr.kek_status, "PENDING")
		self.assertEqual(pr.kek_transaction, po.kek_transaction)

		# Submitting must throw ValidationError because status is PENDING (not Validated/ACKNOWLEDGED)
		self.assertRaises(frappe.ValidationError, pr.submit)

		# 3. Simulate pabean validation on the parent PO
		frappe.db.set_value("Purchase Order", po.name, {
			"kek_status": "Validated",
			"nomor_ppkek": "999888/PPKEK"
		})

		# Re-submit should now succeed
		pr.reload()
		pr.submit()
		self.assertEqual(pr.kek_status, "Validated")
		self.assertEqual(pr.nomor_ppkek, "999888/PPKEK")

	@patch('kek_it_inventory.kek_it_inventory.services.kek_service.post_transaction')
	def test_purchase_receipt_emergency_bypass(self, mock_post):
		# 1. Create and submit Purchase Order (default KEK Status is PENDING)
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"company": "bcmerak",
			"supplier": "_Test Supplier",
			"transaction_date": frappe.utils.today(),
			"schedule_date": frappe.utils.today(),
			"items": [{
				"item_code": "_Test Item",
				"qty": 5,
				"uom": "Nos",
				"rate": 100,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		po.insert()
		po.submit()
		po.reload()

		# 2. Create Purchase Receipt referencing this PO, and enable KEK bypass
		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"company": "bcmerak",
			"supplier": "_Test Supplier",
			"bypass_kek_validation": 1,
			"bypass_reason": "Emergency: INSW portal is down.",
			"items": [{
				"item_code": "_Test Item",
				"qty": 5,
				"uom": "Nos",
				"rate": 100,
				"purchase_order": po.name,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		pr.insert()
		pr.submit()

		# 3. Verify bypass results
		pr.reload()
		self.assertEqual(pr.kek_status, "BYPASSED")
		
		# Verify KEK Inventory Transaction transitioned to Bypassed
		kek_txn_status = frappe.db.get_value("KEK Inventory Transaction", pr.kek_transaction, "status")
		self.assertEqual(kek_txn_status, "Bypassed")

		# Verify audit trail logs (comments) exist
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "KEK Inventory Transaction",
			"reference_name": pr.kek_transaction
		}, fields=["content"])
		
		self.assertTrue(any("Emergency Bypass Enabled" in c.content for c in comments))
		self.assertTrue(any("Emergency: INSW portal is down." in c.content for c in comments))

	@patch('kek_it_inventory.kek_it_inventory.services.kek_service.post_transaction')
	def test_mismatch_engine_detection(self, mock_post):
		# 1. Create and submit Purchase Order
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"company": "bcmerak",
			"supplier": "_Test Supplier",
			"transaction_date": frappe.utils.today(),
			"schedule_date": frappe.utils.today(),
			"items": [{
				"item_code": "_Test Item",
				"qty": 10,
				"uom": "Nos",
				"rate": 100,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		po.insert()
		po.submit()
		po.reload()

		# 2. Manually alter the quantity on the KEK Transaction child table to simulate mismatch
		txn_name = po.kek_transaction
		txn = frappe.get_doc("KEK Inventory Transaction", txn_name)
		txn.items[0].qty = 8  # Mismatch (ERP: 10 vs KEK Transaction: 8)
		txn.save(ignore_permissions=True)

		# 3. Trigger mismatch check engine
		from kek_it_inventory.kek_it_inventory.services.kek_service import check_for_mismatch
		mismatch_found = check_for_mismatch(txn_name)
		self.assertTrue(mismatch_found)

		# 4. Verify statuses updated
		po.reload()
		self.assertEqual(po.kek_status, "MISMATCH")
		
		txn.reload()
		self.assertEqual(txn.status, "FAILED")

		# Verify audit trail comments on KEK Transaction
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "KEK Inventory Transaction",
			"reference_name": txn_name
		}, fields=["content"])
		self.assertTrue(any("Mismatch Detected" in c.content for c in comments))

	@patch('kek_it_inventory.kek_it_inventory.services.kek_service.post_transaction')
	def test_manual_validate_ppkek(self, mock_post):
		# 1. Create and submit Purchase Order
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"company": "bcmerak",
			"supplier": "_Test Supplier",
			"transaction_date": frappe.utils.today(),
			"schedule_date": frappe.utils.today(),
			"items": [{
				"item_code": "_Test Item",
				"qty": 5,
				"uom": "Nos",
				"rate": 100,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		po.insert()
		po.submit()
		po.reload()

		# Ensure roles check passes by patching roles
		with patch('frappe.get_roles', return_value=["KEK Manager"]):
			from kek_it_inventory.kek_it_inventory.services.kek_service import manual_validate_ppkek
			manual_validate_ppkek("Purchase Order", po.name, "PPKEK-TEST-12345")

		# Verify PO is now Validated with the PPKEK number
		po.reload()
		self.assertEqual(po.kek_status, "Validated")
		self.assertEqual(po.nomor_ppkek, "PPKEK-TEST-12345")

		# Verify KEK Transaction transitioned to ACKNOWLEDGED
		txn_status = frappe.db.get_value("KEK Inventory Transaction", po.kek_transaction, "status")
		self.assertEqual(txn_status, "ACKNOWLEDGED")

		# Verify comment was added to the transaction
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "KEK Inventory Transaction",
			"reference_name": po.kek_transaction
		}, fields=["content"])
		self.assertTrue(any("Verifikasi Manual PPKEK" in c.content for c in comments))
		self.assertTrue(any("PPKEK-TEST-12345" in c.content for c in comments))

	def test_download_customs_xls(self):
		# 1. Create Purchase Order
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"company": "bcmerak",
			"supplier": "_Test Supplier",
			"transaction_date": frappe.utils.today(),
			"schedule_date": frappe.utils.today(),
			"items": [{
				"item_code": "_Test Item",
				"qty": 5,
				"uom": "Nos",
				"rate": 100,
				"warehouse": "Test KEK Warehouse - BCM"
			}]
		})
		po.insert()

		# 2. Call download_customs_xls
		from kek_it_inventory.kek_it_inventory.services.kek_service import download_customs_xls
		
		# Reset response dict
		frappe.response = frappe._dict()
		download_customs_xls("Purchase Order", po.name)

		# 3. Assert response fields are set correctly
		self.assertEqual(frappe.response.filename, f"KEK_Items_{po.name}.xlsx")
		self.assertTrue(frappe.response.filecontent)
		self.assertEqual(frappe.response.type, "binary")







