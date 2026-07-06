app_name = "kek_it_inventory"
app_title = "KEK IT Inventory"
app_publisher = "Singlecore"
app_description = "IT Inventory Integrator for KEK PER-24 compliance"
app_email = "admin@singlecore.id"
app_license = "mit"

# Installation
# ------------

# before_install = "kek_it_inventory.install.before_install"
after_install = "kek_it_inventory.kek_it_inventory.setup.seed_master_data"

# Document Events
# ---------------

doc_events = {
	"Purchase Receipt": {
		"on_submit": "kek_it_inventory.kek_it_inventory.api.bridge.create_kek_transaction",
		"on_submit": "kek_it_inventory.services.kek_service.process_pr"	
		},

	"Delivery Note": {
		"on_submit": "kek_it_inventory.kek_it_inventory.api.bridge.create_kek_transaction"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"kek_it_inventory.kek_it_inventory.api.poster.process_queue"
	],
	"daily": [
		"kek_it_inventory.kek_it_inventory.tasks.daily_reconciliation"
	],
}

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			["name", "in", [
				"Purchase Order-custom_sap_po_number",
				"Sales Order-custom_sap_so_number",
			]]
		]
	}
]

