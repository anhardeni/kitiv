import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    
    # Menyiapkan data untuk chart
    chart = get_chart_data(data)
    
    return columns, data, None, chart

def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Transaction ID"),
            "fieldtype": "Link",
            "options": "KEK Inventory Transaction",
            "width": 200
        },
        {
            "fieldname": "transaction_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "payload_kb",
            "label": _("Size (KB)"),
            "fieldtype": "Float",
            "width": 100
        },
        {
            "fieldname": "request_payload",
            "label": _("Request"),
            "fieldtype": "Small Text",
            "width": 300
        },
        {
            "fieldname": "response_payload",
            "label": _("Response"),
            "fieldtype": "Small Text",
            "width": 300
        }
    ]

def get_data(filters):
    conditions = []
    if filters.get("status"):
        conditions.append(f"status = '{filters.get('status')}'")
    if filters.get("from_date"):
        conditions.append(f"transaction_date >= '{filters.get('from_date')}'")
    if filters.get("to_date"):
        conditions.append(f"transaction_date <= '{filters.get('to_date')}'")
        
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    data = frappe.db.sql(f"""
        SELECT 
            name, transaction_date, status, request_payload, response_payload,
            ROUND(LENGTH(request_payload) / 1024, 2) as payload_kb
        FROM `tabKEK Inventory Transaction`
        WHERE {where_clause}
        ORDER BY creation DESC
    """, as_dict=True)
    
    return data

def get_chart_data(data):
    status_counts = {}
    for d in data:
        status_counts[d.status] = status_counts.get(d.status, 0) + 1
        
    return {
        "data": {
            "labels": list(status_counts.keys()),
            "datasets": [{"values": list(status_counts.values())}]
        },
        "type": "percentage" # Pie/Donut style
    }
