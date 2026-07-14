import frappe
from kek_it_inventory.kek_it_inventory.services.manufacture_service import complete_production_stage

def run():
	frappe.set_user("Administrator")
	try:
		res = complete_production_stage("MFG-WO-2026-00003", 50)
		print("API Execution Success! Result:")
		print(res)
		frappe.db.commit()
	except Exception as e:
		print("API Execution Failed! Exception:")
		import traceback
		traceback.print_exc()
