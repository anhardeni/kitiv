import frappe
from frappe.utils import flt, now_datetime

def update_ledger(txn_name):
	"""
	Records movements into KEK Stock Ledger from a SENT transaction.
	"""
	txn = frappe.get_doc("KEK Inventory Transaction", txn_name)
	
	for item in txn.items:
		# 1. Get Previous Balance
		last_balance = frappe.db.get_value("KEK Stock Ledger", 
			{"customs_item_code": item.customs_item_code, "company_profile": txn.company_profile},
			"qty_balance",
			order_by="posting_datetime desc, creation desc"
		)
		
		prev_qty = flt(last_balance)
		
		# 2. Determine In/Out
		qty_in = 0
		qty_out = 0
		
		if txn.transaction_type == "30": # Incoming
			qty_in = flt(item.qty)
			new_balance = prev_qty + qty_in
		elif txn.transaction_type == "31": # Outgoing
			qty_out = flt(item.qty)
			new_balance = prev_qty - qty_out
		else:
			# Handle other types if needed
			new_balance = prev_qty

		# 3. Create Ledger Entry
		ledger_entry = frappe.get_doc({
			"doctype": "KEK Stock Ledger",
			"company_profile": txn.company_profile,
			"posting_datetime": txn.transaction_date or now_datetime(),
			"customs_item_code": item.customs_item_code,
			"transaction_type": txn.transaction_type,
			"voucher_type": txn.erpnext_reference_doctype,
			"voucher_no": txn.erpnext_reference_name,
			"qty_in": qty_in,
			"qty_out": qty_out,
			"qty_balance": new_balance,
			"origin_type": item.origin_type,
			"insw_transaksi_id": txn.insw_transaksi_id
		})
		
		# Bypass read-only if necessary, but since we are in Python, .insert() works
		ledger_entry.insert(ignore_permissions=True)

	frappe.db.commit()
