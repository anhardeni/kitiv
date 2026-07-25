import frappe
from frappe.model.document import Document
import requests
import json
from frappe import _

class KEKAPICredential(Document):
	def validate(self):
		self.validate_uniqueness()

	def before_save(self):
		self.sync_name()

	def sync_name(self):
		if not self.is_new() and self.company_profile and self.environment:
			expected_name = f"KEK-CRED-{self.company_profile}-{self.environment}"
			if self.name != expected_name and not frappe.db.exists("KEK API Credential", expected_name):
				frappe.rename_doc("KEK API Credential", self.name, expected_name, force=True)
				self.name = expected_name


	def validate_uniqueness(self):
		if self.active:
			duplicate = frappe.db.exists("KEK API Credential", {
				"company_profile": self.company_profile,
				"active": 1,
				"name": ["!=", self.name]
			})
			if duplicate:
				frappe.throw(_("There is already an active KEK API Credential ({0}) for Company Profile '{1}'.").format(duplicate, self.company_profile))

	@frappe.whitelist()
	def get_decrypted_keys(self):
		self.check_permission("read")
		return {
			"x_insw_key": self.get_password("x_insw_key"),
			"x_unique_key": self.get_password("x_unique_key")
		}

	@frappe.whitelist()
	def clean_dummy_data(self):
		if self.environment != "DUMMY":
			frappe.throw(_("Cleansing data is only allowed in DUMMY environment."))
		
		# Get NPWP from the related KEK Company Profile
		if not self.company_profile:
			frappe.throw(_("Company Profile is not set on this credential."))
		
		npwp = frappe.db.get_value("KEK Company Profile", self.company_profile, "npwp")
		if not npwp:
			frappe.throw(_("NPWP is not configured in Company Profile '{0}'.").format(self.company_profile))
		
		# Clean NPWP (only digits)
		npwp_cleaned = "".join(filter(str.isdigit, npwp))
		if not npwp_cleaned:
			frappe.throw(_("Cleaned NPWP is empty or invalid."))
		
		# Resolve base url and endpoint
		base_url = self.base_url.strip() if self.base_url else ""
		if "/api/inventory" in base_url:
			endpoint = f"{base_url.rstrip('/')}/temp/transaksi"
		elif "/api-prod/inventory" in base_url:
			endpoint = f"{base_url.rstrip('/')}/temp/transaksi"
		else:
			endpoint = f"{base_url.rstrip('/')}/api/inventory/temp/transaksi"
		
		# Append query parameter
		url = f"{endpoint}?npwp={npwp_cleaned}"
		
		# Headers
		from kek_it_inventory.kek_it_inventory.api.poster import get_unique_key
		insw_key = self.get_password("x_insw_key")
		unique_key = get_unique_key(self) or self.get_password("x_unique_key")
		
		headers = {
			"Content-Type": "application/json",
			"x-insw-key": insw_key,
			"x-unique-key": unique_key
		}
		
		try:
			response = requests.delete(url, headers=headers, timeout=30)
			if response.status_code in [200, 201]:
				# Return response message or success text
				res_msg = response.text or "Data cleansed successfully."
				return res_msg
			else:
				frappe.throw(_("Cleansing failed. API returned status {0}: {1}").format(response.status_code, response.text))
		except Exception as e:
			frappe.throw(_("Connection error during cleansing: {0}").format(str(e)))
