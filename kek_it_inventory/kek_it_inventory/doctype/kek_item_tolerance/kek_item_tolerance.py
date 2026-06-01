import frappe
from frappe.model.document import Document

class KEKItemTolerance(Document):
	def validate(self):
		if float(self.tolerance_percentage) < 0:
			frappe.throw("Persentase batas toleransi tidak boleh bernilai negatif.")
