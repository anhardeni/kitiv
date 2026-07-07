import frappe
from frappe.model.document import Document


class SAPPOImportJob(Document):

	def before_save(self):
		"""Reset progress fields if file changes and status is being re-queued"""
		if self.is_new():
			self.status = "Queued"
			self.total_rows = 0
			self.processed_rows = 0
			self.last_po_number = None
			self.error_log = None

	def after_insert(self):
		"""
		Immediately enqueue the chunked XLS processor after the job record is created.
		User flow:
		  1. Open a new 'SAP PO Import Job'
		  2. Attach an XLS/XLSX file
		  3. Save → this hook fires and queues processing automatically
		"""
		if not self.file_url:
			frappe.throw("Please attach an XLS/XLSX file before saving.")

		self.status = "Queued"
		self.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.enqueue(
			method="kek_it_inventory.kek_it_inventory.api.sap_sync.process_sap_xls_chunked",
			queue="long",
			enqueue_after_commit=True,   # Ensure the job record is committed before processing starts
			timeout=3600,
			# --- actual function argument ---
			job_name=self.name
		)

		frappe.msgprint(
			f"XLS file queued for processing. Job: <b>{self.name}</b>. "
			"Refresh this page to monitor progress.",
			alert=True
		)
