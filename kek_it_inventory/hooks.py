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
	"Purchase Order": {
		"on_submit": "kek_it_inventory.kek_it_inventory.services.kek_service.process_purchase_order"
	},

	"Subcontracting Order": {
		"on_submit": "kek_it_inventory.kek_it_inventory.services.kek_service.process_subcontracting_order"
	},

	"Purchase Receipt": {
		"validate": "kek_it_inventory.kek_it_inventory.services.kek_service.copy_parent_kek_details",
		"before_submit": "kek_it_inventory.kek_it_inventory.services.kek_service.validate_kek_submission",
		"on_submit": "kek_it_inventory.kek_it_inventory.services.kek_service.process_purchase_receipt"
	},

	"Subcontracting Receipt": {
		"validate": "kek_it_inventory.kek_it_inventory.services.kek_service.copy_parent_kek_details",
		"before_submit": "kek_it_inventory.kek_it_inventory.services.kek_service.validate_kek_submission"
	},

	"Delivery Note": {
		"on_update": "kek_it_inventory.kek_it_inventory.services.kek_service.process_delivery_note"
	}
}

doctype_js = {
	"Purchase Order": "public/js/purchase_order.js",
	"Subcontracting Order": "public/js/subcontracting_order.js",
	"Purchase Receipt": "public/js/purchase_receipt.js",
	"Delivery Note": "public/js/delivery_note.js"
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"kek_it_inventory.kek_it_inventory.api.poster.process_queue",
		"kek_it_inventory.kek_it_inventory.services.kek_service.run_mismatch_check_job"
	],
	"cron": {
		# SAP OData Pull - runs every 15 minutes
		# Push endpoint: /api/method/kek_it_inventory.kek_it_inventory.api.sap_sync.receive_sap_document
		"*/15 * * * *": [
			"kek_it_inventory.kek_it_inventory.api.sap_sync.run_po_sync"
		]
	},
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
				"Purchase Receipt-custom_grn_ref",
				"Purchase Receipt-custom_bc_registration_date",
				"Purchase Receipt-custom_bc_registration_no",
				"Purchase Receipt-custom_bc_document_type",
				"Purchase Receipt-custom_custom_no_aju",
				"Delivery Note-custom_bc_registration_date",
				"Delivery Note-custom_bc_registration_no",
				"Delivery Note-custom_bc_document_type",
				"Delivery Note-custom_no_aju",
			]]
		]
	},
	"KEK Ref Transaction Type",
	"KEK Ref Item Category",
	"KEK Ref Customs Document",
	"KEK Ref Unit",
	"KEK Ref Activity Code"
]