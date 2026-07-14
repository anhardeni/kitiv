# Copyright (c) 2026, Singlecore and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.utils import flt
from kek_it_inventory.kek_it_inventory.services.manufacture_service import (
	get_production_stages,
	complete_production_stage,
	create_sub_work_orders,
	ensure_custom_fields
)

class TestManufactureService(unittest.TestCase):
	def setUp(self):
		ensure_custom_fields()
		# Clean up any existing test data to avoid duplicate key errors
		frappe.db.rollback()
		
		# Define test company and warehouses
		self.company = "bcmerak"
		self.warehouses = {
			"raw": "Gudang Bahan Baku - BCM",
			"embroidery": "WIP Embroidery - BCM",
			"cutting": "WIP Cutting - BCM",
			"sewing": "WIP Sewing - BCM",
			"fill_cotton": "WIP Fill Cotton - BCM",
			"fg": "Finished Goods - BCM"
		}
		
		# Create Warehouses if not exist
		for key, wh_name in self.warehouses.items():
			if not frappe.db.exists("Warehouse", wh_name):
				frappe.get_doc({
					"doctype": "Warehouse",
					"warehouse_name": wh_name.replace(" - BCM", ""),
					"company": self.company
				}).insert()
				
		# Define test items
		self.items = {
			"raw_fabric": "Kain Mentah Test",
			"raw_cotton": "Kapas Test",
			"sfg_emb": "Kain Bordir Test",
			"sfg_cut": "Potongan Pola Test",
			"sfg_sew": "Kulit Boneka Test",
			"sfg_fill": "Boneka Isi Test",
			"fg_doll": "Finished Doll Test"
		}
		
		# Create Items if not exist and set default warehouses
		self.create_item(self.items["raw_fabric"], self.warehouses["raw"])
		self.create_item(self.items["raw_cotton"], self.warehouses["raw"])
		self.create_item(self.items["sfg_emb"], self.warehouses["embroidery"])
		self.create_item(self.items["sfg_cut"], self.warehouses["cutting"])
		self.create_item(self.items["sfg_sew"], self.warehouses["sewing"])
		self.create_item(self.items["sfg_fill"], self.warehouses["fill_cotton"])
		self.create_item(self.items["fg_doll"], self.warehouses["fg"])
		
		# Create BOMs
		# 1. Embroidery: Kain Mentah -> Kain Bordir
		self.bom_emb = self.create_bom(self.items["sfg_emb"], [{"item_code": self.items["raw_fabric"], "qty": 1}])
		# 2. Cutting: Kain Bordir -> Potongan Pola
		self.bom_cut = self.create_bom(self.items["sfg_cut"], [{"item_code": self.items["sfg_emb"], "qty": 1}])
		# 3. Sewing: Potongan Pola -> Kulit Boneka
		self.bom_sew = self.create_bom(self.items["sfg_sew"], [{"item_code": self.items["sfg_cut"], "qty": 1}])
		# 4. Fill Cotton: Kulit Boneka + Kapas -> Boneka Isi
		self.bom_fill = self.create_bom(self.items["sfg_fill"], [
			{"item_code": self.items["sfg_sew"], "qty": 1},
			{"item_code": self.items["raw_cotton"], "qty": 1}
		])
		# 5. Stitch Hand: Boneka Isi -> Finished Doll
		self.bom_fg = self.create_bom(self.items["fg_doll"], [{"item_code": self.items["sfg_fill"], "qty": 1}])
		
		# Clean up any existing stock and add new stock of raw materials
		frappe.db.delete("Stock Ledger Entry", {"company": self.company})
		self.add_stock(self.items["raw_fabric"], self.warehouses["raw"], 500, 10000.0) # 500 meters @ Rp 10.000
		self.add_stock(self.items["raw_cotton"], self.warehouses["raw"], 500, 5000.0)  # 500 kg @ Rp 5.000
		
	def tearDown(self):
		frappe.db.rollback()
		
	def create_item(self, item_code, default_wh):
		if not frappe.db.exists("Item", item_code):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"item_defaults": [{
					"company": self.company,
					"default_warehouse": default_wh
				}]
			})
			item.insert()
		else:
			item = frappe.get_doc("Item", item_code)
			found = False
			for d in item.item_defaults:
				if d.company == self.company:
					d.default_warehouse = default_wh
					found = True
					break
			if not found:
				item.append("item_defaults", {
					"company": self.company,
					"default_warehouse": default_wh
				})
			item.save()

	def create_bom(self, item_code, raw_materials):
		# Delete old BOM to avoid duplicate issues
		old_boms = frappe.get_all("BOM", filters={"docstatus": ["<", 2], "item": item_code}, fields=["name"])
		for bom in old_boms:
			frappe.db.set_value("BOM", bom.name, "docstatus", 2) # Cancel
			frappe.db.delete("BOM", bom.name)
			
		bom = frappe.get_doc({
			"doctype": "BOM",
			"item": item_code,
			"quantity": 1,
			"company": self.company,
			"is_active": 1,
			"is_default": 1,
			"items": [{
				"item_code": r["item_code"],
				"qty": r["qty"],
				"uom": "Nos"
			} for r in raw_materials]
		})
		bom.insert()
		bom.submit()
		return bom.name

	def add_stock(self, item_code, warehouse, qty, rate):
		se = frappe.get_doc({
			"doctype": "Stock Entry",
			"purpose": "Material Receipt",
			"stock_entry_type": "Material Receipt",
			"company": self.company,
			"items": [{
				"item_code": item_code,
				"qty": qty,
				"t_warehouse": warehouse,
				"rate": rate,
				"basic_rate": rate,
				"uom": "Nos",
				"expense_account": "Stock Adjustment - BCM" if frappe.db.exists("Account", "Stock Adjustment - BCM") else None
			}]
		})
		se.insert()
		se.submit()

	def test_ideal_flow(self):
		"""Test case for the 100% ideal manufacturing flow (no loss, correct permissions)."""
		# Run as System Manager to guarantee access permissions
		frappe.set_user("Administrator")
		
		# 1. Create and submit main Work Order
		wo = frappe.get_doc({
			"doctype": "Work Order",
			"company": self.company,
			"production_item": self.items["fg_doll"],
			"bom_no": self.bom_fg,
			"qty": 10,
			"wip_warehouse": self.warehouses["fill_cotton"], # main WO WIP
			"fg_warehouse": self.warehouses["fg"]
		})
		wo.insert()
		wo.submit()
		
		# 2. Verify sub-Work Orders were created & submitted automatically
		sub_wos = frappe.get_all("Work Order", filters={"parent_work_order": wo.name}, fields=["name", "production_item", "qty", "status"])
		self.assertEqual(len(sub_wos), 4) # 4 intermediate SFG items
		
		# 3. Fetch stages from dashboard api
		stages = get_production_stages(wo.name)
		self.assertEqual(len(stages), 5) # 4 sub-WOs + 1 parent WO
		
		# 4. Perform sequential execution stage-by-stage
		for idx in range(5):
			stage = stages[idx]
			self.assertEqual(stage["status"], "Not Started")
			
			# Complete the stage
			res = complete_production_stage(stage["work_order"], stage["target_qty"])
			self.assertEqual(res["status"], "Success")
			self.assertEqual(res["wo_status"], "Completed")
			
			# Reload stages to update visual status
			stages = get_production_stages(wo.name)
			
		# Verify final WO status is Completed
		wo.reload()
		self.assertEqual(wo.status, "Completed")
		
		# Verify final Finished Goods Stock Balance
		fg_stock = frappe.db.get_value("Bin", {"item_code": self.items["fg_doll"], "warehouse": self.warehouses["fg"]}, "actual_qty")
		self.assertEqual(flt(fg_stock), 10.0)

	def test_role_based_permissions(self):
		"""Test case to ensure only users with the correct roles can complete stages."""
		# Create a dummy user and remove manufacturing roles
		user_name = "test_operator@example.com"
		if not frappe.db.exists("User", user_name):
			user = frappe.get_doc({
				"doctype": "User",
				"email": user_name,
				"first_name": "Test",
				"roles": [{"role": "Blogger"}] # Non-authorized role
			}).insert()
		else:
			user = frappe.get_doc("User", user_name)
			user.roles = [{"role": "Blogger"}]
			user.save()
			
		# Create Work Order
		frappe.set_user("Administrator")
		wo = frappe.get_doc({
			"doctype": "Work Order",
			"company": self.company,
			"production_item": self.items["fg_doll"],
			"bom_no": self.bom_fg,
			"qty": 10,
			"wip_warehouse": self.warehouses["fill_cotton"],
			"fg_warehouse": self.warehouses["fg"]
		}).insert()
		wo.submit()
		
		stages = get_production_stages(wo.name)
		stage1_wo = stages[0]["work_order"]
		
		# Switch user to non-authorized test operator
		frappe.set_user(user_name)
		
		# Trying to complete stage should throw PermissionError
		with self.assertRaises(frappe.PermissionError):
			complete_production_stage(stage1_wo, 10)
			
		# Switch user back
		frappe.set_user("Administrator")

	def test_fuzzy_flow_with_loss(self):
		"""Test case for fuzzy condition: yield loss at intermediate stages and target adjustment."""
		frappe.set_user("Administrator")
		
		# 1. Create and submit main Work Order for 100 Dolls
		wo = frappe.get_doc({
			"doctype": "Work Order",
			"company": self.company,
			"production_item": self.items["fg_doll"],
			"bom_no": self.bom_fg,
			"qty": 100,
			"wip_warehouse": self.warehouses["fill_cotton"],
			"fg_warehouse": self.warehouses["fg"]
		}).insert()
		wo.submit()
		
		# 2. Stage 1 (Embroidery): Complete only 90 pcs (10 scrap/loss)
		stages = get_production_stages(wo.name)
		complete_production_stage(stages[0]["work_order"], 90)
		
		# Verify Stage 2, 3, 4, and 5 Work Order target quantities are adjusted to 90
		stages = get_production_stages(wo.name)
		for idx in range(1, 5):
			self.assertEqual(stages[idx]["target_qty"], 90.0)
			
		# 3. Stage 2 (Cutting): Complete all 90 pcs
		complete_production_stage(stages[1]["work_order"], 90)
		
		# 4. Stage 3 (Sewing): Complete only 85 pcs (5 scrap/loss)
		stages = get_production_stages(wo.name)
		complete_production_stage(stages[2]["work_order"], 85)
		
		# Verify Stage 4 and 5 target quantities are adjusted to 85
		stages = get_production_stages(wo.name)
		for idx in range(3, 5):
			self.assertEqual(stages[idx]["target_qty"], 85.0)
			
		# 5. Complete remaining stages
		complete_production_stage(stages[3]["work_order"], 85)
		complete_production_stage(stages[4]["work_order"], 85)
		
		# Verify final Work Order is completed with 85 finished items
		wo.reload()
		self.assertEqual(wo.status, "Completed")
		
		fg_stock = frappe.db.get_value("Bin", {"item_code": self.items["fg_doll"], "warehouse": self.warehouses["fg"]}, "actual_qty")
		self.assertEqual(flt(fg_stock), 85.0)

	def test_insufficient_stock_validation(self):
		"""Test case for fuzzy condition: stock validation triggers when raw material stock is depleted."""
		frappe.set_user("Administrator")
		
		# Set raw material fabric stock to 0
		frappe.db.delete("Stock Ledger Entry", {"company": self.company})
		# Add a small amount of Cotton, but NO Fabric
		self.add_stock(self.items["raw_cotton"], self.warehouses["raw"], 10, 5000.0)
		
		# Create Work Order
		wo = frappe.get_doc({
			"doctype": "Work Order",
			"company": self.company,
			"production_item": self.items["fg_doll"],
			"bom_no": self.bom_fg,
			"qty": 10,
			"wip_warehouse": self.warehouses["fill_cotton"],
			"fg_warehouse": self.warehouses["fg"]
		}).insert()
		wo.submit()
		
		stages = get_production_stages(wo.name)
		
		# Completing Stage 1 (Embroidery) requires Kain Mentah, which has 0 stock.
		# This should raise standard Stock Error in ERPNext (ValidationError or similar).
		# In ERPNext, the stock validation is typically raised as frappe.ValidationError.
		# Let's assert that it raises ValidationError.
		with self.assertRaises(frappe.ValidationError):
			complete_production_stage(stages[0]["work_order"], 10)
