import frappe

def setup_test_role_permissions():
	role_name = "_Test Role"
	
	# 1. Ensure the Role exists
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc({
			"doctype": "Role",
			"role_name": role_name,
			"desk_access": 1
		}).insert(ignore_permissions=True)
		print(f"Created Role: {role_name}")

	# 2. DocTypes in kek_it_inventory that need permission assignment
	kek_doctypes = [
		"KEK Inventory Transaction",
		"KEK Company Profile",
		"KEK API Credential",
		"KEK Item Mapping",
		"KEK Item Tolerance",
		"KEK Ref Transaction Type",
		"KEK Ref Customs Document",
		"KEK Ref Item Category",
		"KEK Ref Unit",
		"KEK Ref Activity Code",
		"KEK Stock Ledger",
		"KEK Stock Snapshot"
	]

	for doctype in kek_doctypes:
		# Check and add custom permission
		if frappe.db.exists("DocType", doctype):
			has_perm = frappe.db.exists("Custom DocPerm", {
				"parent": doctype,
				"role": role_name
			})
			if not has_perm:
				frappe.get_doc({
					"doctype": "Custom DocPerm",
					"parent": doctype,
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": role_name,
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
					"export": 1,
					"print": 1,
					"report": 1,
					"share": 1,
					"permlevel": 0
				}).insert(ignore_permissions=True)
				print(f"Added permissions to {doctype} for {role_name}")
				
	frappe.clear_cache()
	frappe.db.commit()

def setup_kek_manager_permissions():
	role_name = "KEK Manager"
	
	# 1. Ensure the Role exists
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc({
			"doctype": "Role",
			"role_name": role_name,
			"desk_access": 1
		}).insert(ignore_permissions=True)
		print(f"Created Role: {role_name}")

	# 2. DocTypes in kek_it_inventory that need permission assignment
	kek_doctypes = [
		"KEK Inventory Transaction",
		"KEK Company Profile",
		"KEK API Credential",
		"KEK Item Mapping",
		"KEK Item Tolerance",
		"KEK Ref Transaction Type",
		"KEK Ref Customs Document",
		"KEK Ref Item Category",
		"KEK Ref Unit",
		"KEK Ref Activity Code",
		"KEK Stock Ledger",
		"KEK Stock Snapshot",
		"KEK Compliance Archive"
	]

	for doctype in kek_doctypes:
		# Check and add custom permission
		if frappe.db.exists("DocType", doctype):
			has_perm = frappe.db.exists("Custom DocPerm", {
				"parent": doctype,
				"role": role_name
			})
			if not has_perm:
				frappe.get_doc({
					"doctype": "Custom DocPerm",
					"parent": doctype,
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": role_name,
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
					"export": 1,
					"print": 1,
					"report": 1,
					"share": 1,
					"permlevel": 0
				}).insert(ignore_permissions=True)
				print(f"Added permissions to {doctype} for {role_name}")
				
	frappe.clear_cache()
	frappe.db.commit()

def setup_kek_user_permissions():
	role_name = "KEK User"
	
	# 1. Ensure the Role exists
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc({
			"doctype": "Role",
			"role_name": role_name,
			"desk_access": 1
		}).insert(ignore_permissions=True)
		print(f"Created Role: {role_name}")

	# 2. DocTypes in kek_it_inventory that need permission assignment
	kek_doctypes = [
		"KEK Inventory Transaction",
		"KEK Company Profile",
		"KEK API Credential",
		"KEK Item Mapping",
		"KEK Item Tolerance",
		"KEK Ref Transaction Type",
		"KEK Ref Customs Document",
		"KEK Ref Item Category",
		"KEK Ref Unit",
		"KEK Ref Activity Code",
		"KEK Stock Ledger",
		"KEK Stock Snapshot",
		"KEK Compliance Archive"
	]

	for doctype in kek_doctypes:
		# Check and add custom permission
		if frappe.db.exists("DocType", doctype):
			has_perm = frappe.db.exists("Custom DocPerm", {
				"parent": doctype,
				"role": role_name
			})
			if not has_perm:
				frappe.get_doc({
					"doctype": "Custom DocPerm",
					"parent": doctype,
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": role_name,
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 0,
					"export": 1,
					"print": 1,
					"report": 1,
					"share": 1,
					"permlevel": 0
				}).insert(ignore_permissions=True)
				print(f"Added permissions to {doctype} for {role_name}")
			else:
				# update permission to delete: 0, and ensure others are 1
				doc = frappe.get_doc("Custom DocPerm", has_perm)
				updated = False
				for field in ["read", "write", "create", "export", "print", "report", "share"]:
					if doc.get(field) != 1:
						doc.set(field, 1)
						updated = True
				if doc.delete != 0:
					doc.delete = 0
					updated = True
				if updated:
					doc.save(ignore_permissions=True)
					print(f"Updated permissions for {doctype} for {role_name}")
				
	frappe.clear_cache()
	frappe.db.commit()


