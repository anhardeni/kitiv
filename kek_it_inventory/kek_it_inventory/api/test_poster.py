import frappe
from frappe.tests.utils import FrappeTestCase
from kek_it_inventory.kek_it_inventory.api.poster import post_transaction
from unittest.mock import patch, MagicMock
import json

class TestPosterAPI(FrappeTestCase):
    
	def setUp(self):
		"""
		Fungsi ini berjalan otomatis sebelum setiap test dijalankan.
		FrappeTestCase akan melakukan ROLLBACK otomatis setelah test selesai.
		"""
		self.company_profile = "TEST-PROFILE-API"
		
		# 1. Setup Data Master (Company Profile)
		if not frappe.db.exists("KEK Company Profile", self.company_profile):
			frappe.get_doc({
				"doctype": "KEK Company Profile",
				"company_name": self.company_profile,
				"npwp": "012345678901234",
				"nib": "1234567890123",
				"erpnext_company": "bcmerak"
			}).insert()

		# 2. Setup Data Master (API Credential)
		if not frappe.db.exists("KEK API Credential", {"company_profile": self.company_profile}):
			frappe.get_doc({
				"doctype": "KEK API Credential",
				"company_profile": self.company_profile,
				"base_url": "https://api.example.com",
				"x_insw_key": "dummy-key",
				"x_unique_key": "dummy-unique",
				"active": 1
			}).insert()

		# 3. Setup Data Transaksi dengan Child Table
		self.txn = frappe.get_doc({
			"doctype": "KEK Inventory Transaction",
			"company_profile": self.company_profile,
			"transaction_date": frappe.utils.today(),
			"transaction_type": "30", # Pemasukan
			"erpnext_reference_doctype": "Purchase Receipt",
			"erpnext_reference_name": "MAT-PRE-TEST-UNIT",
			"items": [
				{
					"customs_item_code": "BRG-KEK-001",
					"category_code": "1",
					"item_name_customs": "Bahan Baku Utama",
					"qty": 500,
					"uom_code": "KGM",
					"amount_idr": 25000000,
					"origin_type": "TLDDP",
					"business_flow_type": "PROCESSING"
				}
			]
		}).insert(ignore_links=True)
		
		# Frappe drops grandchild tables during parent insert, we must insert manually
		frappe.get_doc({
			"doctype": "KEK Item Customs Doc",
			"parent": self.txn.items[0].name,
			"parenttype": "KEK Inventory Transaction Item",
			"parentfield": "customs_docs",
			"customs_doc_code": "0407021",
			"customs_doc_number": "000888/BC21/2026",
			"customs_doc_date": "2026-05-10"
		}).insert(ignore_permissions=True)
		
		# Bersihkan cache untuk mencegah TimestampMismatchError di poster.py
		frappe.db.commit()
		if hasattr(frappe.local, 'document_cache'):
			frappe.local.document_cache.clear()

	@patch('kek_it_inventory.kek_it_inventory.api.poster.get_unique_key')
	@patch('kek_it_inventory.kek_it_inventory.api.poster.requests.post')
	def test_payload_structure_camelcase_and_nested(self, mock_post, mock_key):
		"""
		Menguji apakah payload JSON yang dibentuk sesuai dengan standar KEK.PDF
		"""
		# Setup Mock
		mock_key.return_value = "MOCK-UNIQUE-KEY-123"
		
		# Tangkap argumen yang diteruskan ke requests.post
		captured_payload = {}
		def side_effect(url, data, headers, timeout):
			nonlocal captured_payload
			captured_payload = json.loads(data)
			class MockResponse:
				def __init__(self):
					self.status_code = 200
					self.text = '{"status": true, "code": "01", "data": {"resultDataTransaksi": [{"idTransaksi": "SINSW-TX-999-OK"}]}}'
				def json(self): return json.loads(self.text)
			return MockResponse()
			
		mock_post.side_effect = side_effect
		
		# Eksekusi
		post_transaction(self.txn.name)
		
		# Asersi (Assertion): Verifikasi bahwa tidak ada error & payload sukses tertangkap
		self.assertTrue(captured_payload, "Payload gagal ditangkap oleh mock.")
		
		# Asersi Struktur Dasar
		self.assertIn("data", captured_payload)
		self.assertEqual(len(captured_payload["data"]), 1)
		
		data_node = captured_payload["data"][0]
		
		# Asersi Level 1: Meta Transaksi (CamelCase strict)
		self.assertIn("kdKegiatan", data_node)
		self.assertEqual(data_node["kdKegiatan"], "30")
		self.assertIn("dokumenKegiatan", data_node)
		
		doc_node = data_node["dokumenKegiatan"][0]
		self.assertEqual(doc_node["nomorDokKegiatan"], "MAT-PRE-TEST-UNIT")
		self.assertIn("barangTransaksi", doc_node)
		
		item_node = doc_node["barangTransaksi"][0]
		
		# Asersi Level 2: Item Barang
		self.assertEqual(item_node["kdBarang"], "BRG-KEK-001")
		self.assertEqual(item_node["jumlah"], 500)
		self.assertEqual(item_node["kdSatuan"], "KGM")
		self.assertIn("dokumen", item_node)
		
		# Asersi Level 3: Dokumen Pabean (Nested Array)
		customs_doc_node = item_node["dokumen"][0]
		self.assertEqual(customs_doc_node["kodeDokumen"], "0407021")
		self.assertEqual(customs_doc_node["nomorDokumen"], "000888/BC21/2026")
		self.assertEqual(customs_doc_node["tanggalDokumen"], "10-05-2026") # Verifikasi format DD-MM-YYYY
