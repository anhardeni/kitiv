import frappe
from frappe.tests.utils import FrappeTestCase

class TestKEKAPICredential(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("KEK API Credential", {"company_profile": ["like", "TEST UPDATE PROFILE%"]})
		frappe.db.delete("KEK Company Profile", {"company_name": "Test Update Profile Co"})
		profile = frappe.get_doc({
			"doctype": "KEK Company Profile",
			"company_name": "Test Update Profile Co",
			"erpnext_company": "bcmerak",
			"npwp": "123456789012345",
			"nib": "1234567890"
		})
		profile.insert(ignore_permissions=True)
		self.profile_name = profile.name

	def test_update_credential_fields_and_rename(self):
		cred = frappe.get_doc({
			"doctype": "KEK API Credential",
			"company_profile": self.profile_name,
			"environment": "DUMMY",
			"active": 1,
			"base_url": "https://dummy.example.com",
			"x_insw_key": "initial_key",
			"x_unique_key": "initial_unique"
		})
		cred.insert(ignore_permissions=True)
		expected_initial_name = f"KEK-CRED-{self.profile_name}-DUMMY"
		self.assertEqual(cred.name, expected_initial_name)

		# Update fields: environment, active, base_url, keys
		cred.environment = "REAL"
		cred.active = 1
		cred.base_url = "https://real.example.com"
		cred.x_insw_key = "new_insw_key"
		cred.x_unique_key = "new_unique_key"
		cred.save(ignore_permissions=True)

		# Verify document was automatically renamed to match environment
		expected_real_name = f"KEK-CRED-{self.profile_name}-REAL"
		self.assertEqual(cred.name, expected_real_name)
		
		# Fetch reloaded doc to verify fields
		reloaded = frappe.get_doc("KEK API Credential", expected_real_name)
		self.assertEqual(reloaded.environment, "REAL")
		self.assertEqual(reloaded.base_url, "https://real.example.com")
		self.assertEqual(reloaded.get_password("x_insw_key"), "new_insw_key")
		self.assertEqual(reloaded.get_password("x_unique_key"), "new_unique_key")

	def tearDown(self):
		frappe.db.delete("KEK API Credential", {"company_profile": ["like", "TEST UPDATE PROFILE%"]})
		frappe.db.delete("KEK Company Profile", {"company_name": "Test Update Profile Co"})
