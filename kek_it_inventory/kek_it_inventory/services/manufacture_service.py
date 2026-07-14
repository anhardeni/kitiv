# Copyright (c) 2026, Singlecore and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

def ensure_custom_fields():
	"""Ensures that the custom parent_work_order field exists in the Work Order Doctype."""
	if not frappe.db.exists("Custom Field", "Work Order-parent_work_order"):
		frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Work Order",
			"fieldname": "parent_work_order",
			"label": "Parent Work Order",
			"fieldtype": "Link",
			"options": "Work Order",
			"insert_after": "company"
		}).insert()
		frappe.clear_cache(doctype="Work Order")

def check_manufacture_permission():
	"""Checks if the current user has permission to process manufacture stages."""
	roles = frappe.get_roles()
	allowed_roles = ["Manufacturing User", "Manufacturing Manager", "System Manager"]
	if not any(role in roles for role in allowed_roles):
		frappe.throw(
			_("Anda tidak memiliki hak akses (Role) yang sesuai untuk memproses tahapan manufaktur ini. Diperlukan Role Manufacturing User atau Manager."),
			frappe.PermissionError
		)

def get_item_default_warehouse(item_code, company=None):
	"""Retrieves the default warehouse of an item for the specified company (child table: item_defaults)."""
	if not company:
		company = frappe.defaults.get_default("company") or frappe.db.get_default("company")
		
	default_wh = frappe.db.get_value("Item Default", 
		{"parent": item_code, "company": company}, 
		"default_warehouse"
	)
	if not default_wh:
		default_wh = frappe.db.get_value("Item Default", 
			{"parent": item_code}, 
			"default_warehouse"
		)
	return default_wh

@frappe.whitelist()
def get_production_stages(work_order_name):
	"""
	Traces the BOM hierarchy and returns the 5 stages of production,
	along with their status, target qty, and associated Work Orders.
	"""
	ensure_custom_fields()
	parent_wo = frappe.get_doc("Work Order", work_order_name)
	
	# Trace the BOM chain to get sub-assemblies in bottom-to-top order
	stages_hierarchy = get_bom_hierarchy(parent_wo.bom_no, parent_wo.qty)
	
	# Add the parent Work Order itself as the final stage
	stages_hierarchy.append({
		"item_code": parent_wo.production_item,
		"bom_no": parent_wo.bom_no,
		"qty": parent_wo.qty,
		"is_parent": True
	})
	
	# Gather all sub-Work Orders linked to this parent
	sub_wos = frappe.get_all("Work Order", 
		filters={"parent_work_order": work_order_name, "docstatus": ["<", 2]},
		fields=["name", "production_item", "status", "qty", "produced_qty", "wip_warehouse", "docstatus"]
	)
	
	wo_map = {wo.production_item: wo for wo in sub_wos}
	
	stages = []
	for idx, s in enumerate(stages_hierarchy):
		item_desc = frappe.db.get_value("Item", s["item_code"], "item_name") or s["item_code"]
		default_wip = get_item_default_warehouse(s["item_code"], parent_wo.company)
		
		# Find the Work Order for this stage
		if s.get("is_parent"):
			linked_wo = parent_wo.name
			status = parent_wo.status
			target_qty = parent_wo.qty
			produced_qty = parent_wo.produced_qty
			wip_wh = parent_wo.wip_warehouse
			docstatus = parent_wo.docstatus
		else:
			wo = wo_map.get(s["item_code"])
			if wo:
				linked_wo = wo.name
				status = wo.status
				target_qty = wo.qty
				produced_qty = wo.produced_qty
				wip_wh = wo.wip_warehouse
				docstatus = wo.docstatus
			else:
				linked_wo = None
				status = "Draft"
				target_qty = s["qty"]
				produced_qty = 0
				wip_wh = default_wip
				docstatus = 0
				
		stages.append({
			"stage_index": idx,
			"item_code": s["item_code"],
			"item_name": item_desc,
			"bom_no": s["bom_no"],
			"work_order": linked_wo,
			"status": status,
			"docstatus": docstatus,
			"target_qty": flt(target_qty),
			"produced_qty": flt(produced_qty),
			"wip_warehouse": wip_wh
		})
		
	return stages

def get_bom_hierarchy(bom_no, parent_qty):
	"""Recursively traverses the BOM to build a bottom-up list of sub-assemblies."""
	sub_assemblies = []
	
	def recurse(current_bom_no, qty):
		bom = frappe.get_doc("BOM", current_bom_no)
		for item in bom.items:
			if item.bom_no:
				# Calculate required qty based on parent BOM basis
				req_qty = (flt(item.qty) / flt(bom.quantity)) * flt(qty)
				# Recurse first (deepest first)
				recurse(item.bom_no, req_qty)
				# Add to list
				sub_assemblies.append({
					"item_code": item.item_code,
					"bom_no": item.bom_no,
					"qty": req_qty
				})
				
	recurse(bom_no, parent_qty)
	
	# De-duplicate while preserving order (bottom-up)
	seen = set()
	unique_subs = []
	for s in sub_assemblies:
		if s["item_code"] not in seen:
			seen.add(s["item_code"])
			unique_subs.append(s)
			
	return unique_subs

def create_sub_work_orders(doc, method):
	"""
	Hook triggered on_submit of the main Work Order.
	Automatically generates and submits sub-Work Orders for all intermediate stages.
	"""
	ensure_custom_fields()
	# If this is already a sub-Work Order, do nothing to avoid infinite loops
	if doc.get("parent_work_order"):
		return
		
	# Get the BOM hierarchy
	stages = get_bom_hierarchy(doc.bom_no, doc.qty)
	
	for s in stages:
		# Check if sub-Work Order already exists
		exists = frappe.db.exists("Work Order", {
			"parent_work_order": doc.name,
			"production_item": s["item_code"],
			"docstatus": ["<", 2]
		})
		if exists:
			continue
			
		# Get default WIP warehouse from Item Master
		wip_wh = get_item_default_warehouse(s["item_code"], doc.company)
		if not wip_wh:
			frappe.throw(_("Item {0} tidak memiliki Default Warehouse di Item Master. Silakan atur terlebih dahulu agar WIP warehouse dapat diatur otomatis.", [s["item_code"]]))
			
		# Create sub-Work Order
		sub_wo = frappe.get_doc({
			"doctype": "Work Order",
			"company": doc.company,
			"production_item": s["item_code"],
			"bom_no": s["bom_no"],
			"qty": s["qty"],
			"wip_warehouse": wip_wh,
			"fg_warehouse": wip_wh,  # SFG output is stored in its own WIP warehouse
			"parent_work_order": doc.name,
			"use_multi_level_bom": 0,
			"planned_start_date": doc.planned_start_date,
			"planned_end_date": doc.planned_end_date
		})
		sub_wo.insert()
		sub_wo.submit()

@frappe.whitelist()
def complete_production_stage(work_order_name, actual_qty):
	"""
	Creates and submits a Manufacture Stock Entry for a stage's Work Order.
	Consumes raw materials from their default warehouses and outputs the SFG to current WIP.
	Also updates subsequent stages' targets if actual_qty < target_qty.
	"""
	check_manufacture_permission()
	ensure_custom_fields()
	
	wo = frappe.get_doc("Work Order", work_order_name)
	actual_qty = flt(actual_qty)
	
	if wo.docstatus != 1:
		frappe.throw(_("Work Order {0} belum di-submit.", [work_order_name]))
		
	if wo.status == "Completed":
		frappe.throw(_("Work Order {0} sudah selesai diproduksi.", [work_order_name]))
		
	# Create Stock Entry of type Manufacture
	se_result = make_stock_entry(wo.name, "Manufacture", actual_qty)
	
	# Determine if se_result is document name or document object
	if isinstance(se_result, str):
		se = frappe.get_doc("Stock Entry", se_result)
	else:
		se = se_result
		if isinstance(se, dict):
			se = frappe.get_doc(se)
	
	# Override source warehouse for raw materials to their default warehouses
	# to avoid consuming from the WO's WIP warehouse directly
	for item in se.items:
		if not item.is_finished_item:
			default_wh = get_item_default_warehouse(item.item_code, wo.company)
			if default_wh:
				item.s_warehouse = default_wh
				
	se.insert()
	se.submit()
	
	# Reload WO to get updated status
	wo.reload()
	
	# If this is a sub-Work Order and actual_qty is less than planned target,
	# propagate the loss to all subsequent stages.
	if wo.get("parent_work_order"):
		parent_wo = frappe.get_doc("Work Order", wo.get("parent_work_order"))
		adjust_subsequent_wos(parent_wo.name, wo.production_item, actual_qty)
	
	return {"status": "Success", "stock_entry": se.name, "wo_status": wo.status}

def adjust_subsequent_wos(parent_wo_name, completed_item_code, actual_qty):
	"""Adjusts the target quantities of all subsequent stages in the pipeline."""
	stages = get_production_stages(parent_wo_name)
	
	# Find the index of the completed stage
	completed_idx = -1
	for s in stages:
		if s["item_code"] == completed_item_code:
			completed_idx = s["stage_index"]
			break
			
	if completed_idx == -1:
		return
		
	# Update all subsequent stages' targets
	for s in stages:
		if s["stage_index"] > completed_idx and s["work_order"]:
			sub_wo = frappe.get_doc("Work Order", s["work_order"])
			if sub_wo.status != "Completed":
				# Directly update target qty and recalculate raw materials requirement
				sub_wo.qty = actual_qty
				sub_wo.set_required_items()
				sub_wo.db_update()
				
				# Save all required items child table rows
				for req_item in sub_wo.required_items:
					req_item.db_update()
