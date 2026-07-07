import frappe

def create_number_cards():
    cards = [
        {
            "name": "Total KEK Transactions",
            "label": "Total KEK Transactions",
            "document_type": "KEK Inventory Transaction",
            "filters_json": "[]",
            "function": "Count"
        },
        {
            "name": "Pending ACK",
            "label": "Pending ACK",
            "document_type": "KEK Inventory Transaction",
            "filters_json": "[[\"KEK Inventory Transaction\",\"status\",\"in\",[\"QUEUED\",\"SENT\"]]]",
            "function": "Count"
        },
        {
            "name": "Failed Transmission",
            "label": "Failed Transmission",
            "document_type": "KEK Inventory Transaction",
            "filters_json": "[[\"KEK Inventory Transaction\",\"status\",\"=\",\"FAILED\"]]",
            "function": "Count"
        }
    ]
    
    for c in cards:
        if frappe.db.exists("Number Card", c["name"]):
            frappe.delete_doc("Number Card", c["name"], force=True)
            
        doc = frappe.get_doc({
            "doctype": "Number Card",
            "name": c["name"],
            "label": c["label"],
            "document_type": c["document_type"],
            "filters_json": c["filters_json"],
            "function": c["function"],
            "is_public": 1,
            "is_standard": 1,
            "module": "Kek It Inventory",
            "type": "Document Type"
        })
        doc.insert()
    print("Created KEK IT Inventory Number Cards.")

def main():
    frappe.connect()
    
    # Ensure number cards exist
    create_number_cards()
    
    ws_name = "KEK IT Inventory"
    if frappe.db.exists("Workspace", ws_name):
        frappe.delete_doc("Workspace", ws_name, force=True)
        print(f"Deleted existing KEK IT Inventory workspace to recreate.")
        
    # Standard EditorJS compliant content blocks mapping exactly to shortcuts, cards, and number cards
    content_blocks = [
        {
            "id": "kek_intro_hdr",
            "type": "header",
            "data": {
                "text": "<span class=\"h3\"><b>KEK IT Customs Inventory Dashboard</b></span>",
                "col": 12
            }
        },
        {
            "id": "kek_cards_spc_top",
            "type": "spacer",
            "data": {
                "col": 12
            }
        },
        {
            "id": "kek_nc_1",
            "type": "number_card",
            "data": {
                "number_card_name": "Total KEK Transactions",
                "col": 4
            }
        },
        {
            "id": "kek_nc_2",
            "type": "number_card",
            "data": {
                "number_card_name": "Pending ACK",
                "col": 4
            }
        },
        {
            "id": "kek_nc_3",
            "type": "number_card",
            "data": {
                "number_card_name": "Failed Transmission",
                "col": 4
            }
        },
        {
            "id": "kek_ops_spc",
            "type": "spacer",
            "data": {
                "col": 12
            }
        },
        {
            "id": "kek_ops_hdr",
            "type": "header",
            "data": {
                "text": "<span class=\"h4\"><b>Declaration Operations</b></span>",
                "col": 12
            }
        },
        {
            "id": "kek_sh_1",
            "type": "shortcut",
            "data": {
                "shortcut_name": "New PPKEK Transaction",
                "col": 3
            }
        },
        {
            "id": "kek_sh_2",
            "type": "shortcut",
            "data": {
                "shortcut_name": "Transaction Queue",
                "col": 3
            }
        },
        {
            "id": "kek_sh_3",
            "type": "shortcut",
            "data": {
                "shortcut_name": "Stock Ledger Audit",
                "col": 3
            }
        },
        {
            "id": "kek_sh_4",
            "type": "shortcut",
            "data": {
                "shortcut_name": "Compliance Archive",
                "col": 3
            }
        },
        {
            "id": "kek_sh_sales_order",
            "type": "shortcut",
            "data": {
                "shortcut_name": "Sales Order",
                "col": 3
            }
        },
        {
            "id": "kek_sh_purchase_order",
            "type": "shortcut",
            "data": {
                "shortcut_name": "Purchase Order",
                "col": 3
            }
        },
        {
            "id": "kek_sh_purchase_receipt",
            "type": "shortcut",
            "data": {
                "shortcut_name": "Purchase Receipt",
                "col": 3
            }
        },
        {
            "id": "kek_sh_delivery_note",
            "type": "shortcut",
            "data": {
                "shortcut_name": "Delivery Note",
                "col": 3
            }
        },
        {
            "id": "kek_cards_spc",
            "type": "spacer",
            "data": {
                "col": 12
            }
        },
        {
            "id": "kek_cards_hdr",
            "type": "header",
            "data": {
                "text": "<span class=\"h4\"><b>Reference Modules &amp; Parameters</b></span>",
                "col": 12
            }
        },
        {
            "id": "kek_card_brk_1",
            "type": "card",
            "data": {
                "card_name": "Filing Master",
                "col": 4
            }
        },
        {
            "id": "kek_card_brk_2",
            "type": "card",
            "data": {
                "card_name": "Settings & Mappings",
                "col": 4
            }
        }
    ]

    import json
    doc = frappe.get_doc({
        "doctype": "Workspace",
        "name": ws_name,
        "title": ws_name,
        "icon": "inventory",
        "is_standard": 1,
        "public": 1,
        "module": "Kek It Inventory",
        "label": "KEK IT Inventory",
        "content": json.dumps(content_blocks),
        "number_cards": [
            {
                "number_card_name": "Total KEK Transactions",
                "label": "Total KEK Transactions"
            },
            {
                "number_card_name": "Pending ACK",
                "label": "Pending ACK"
            },
            {
                "number_card_name": "Failed Transmission",
                "label": "Failed Transmission"
            }
        ],
        "shortcuts": [
            {
                "label": "New PPKEK Transaction",
                "type": "DocType",
                "link_to": "KEK Inventory Transaction",
                "doc_view": "New",
                "icon": "plus",
                "color": "Green"
            },
            {
                "label": "Transaction Queue",
                "type": "DocType",
                "link_to": "KEK Inventory Transaction",
                "doc_view": "List",
                "icon": "list",
                "color": "Orange"
            },
            {
                "label": "Stock Ledger Audit",
                "type": "DocType",
                "link_to": "KEK Stock Ledger",
                "doc_view": "List",
                "icon": "database",
                "color": "Blue"
            },
            {
                "label": "Compliance Archive",
                "type": "DocType",
                "link_to": "KEK Compliance Archive",
                "doc_view": "List",
                "icon": "archive",
                "color": "Grey"
            },
            {
                "label": "Sales Order",
                "type": "DocType",
                "link_to": "Sales Order",
                "doc_view": "List",
                "icon": "file-text",
                "color": "Purple"
            },
            {
                "label": "Purchase Order",
                "type": "DocType",
                "link_to": "Purchase Order",
                "doc_view": "List",
                "icon": "credit-card",
                "color": "Red"
            },
            {
                "label": "Purchase Receipt",
                "type": "DocType",
                "link_to": "Purchase Receipt",
                "doc_view": "List",
                "icon": "check-square",
                "color": "Blue"
            },
            {
                "label": "Delivery Note",
                "type": "DocType",
                "link_to": "Delivery Note",
                "doc_view": "List",
                "icon": "truck",
                "color": "Grey"
            }
        ],
        "links": [
            {
                "label": "Filing Master",
                "type": "Card Break",
                "hidden": 0,
                "onboard": 0
            },
            {
                "label": "KEK Inventory Transaction",
                "type": "Link",
                "link_to": "KEK Inventory Transaction",
                "link_type": "DocType",
                "hidden": 0,
                "onboard": 0
            },
            {
                "label": "KEK Stock Ledger",
                "type": "Link",
                "link_to": "KEK Stock Ledger",
                "link_type": "DocType",
                "hidden": 0,
                "onboard": 0
            },
            {
                "label": "KEK Compliance Archive",
                "type": "Link",
                "link_to": "KEK Compliance Archive",
                "link_type": "DocType",
                "hidden": 0,
                "onboard": 0
            },
            {
                "label": "Settings & Mappings",
                "type": "Card Break",
                "hidden": 0,
                "onboard": 0
            },
            {
                "label": "KEK Item Mapping",
                "type": "Link",
                "link_to": "KEK Item Mapping",
                "link_type": "DocType",
                "hidden": 0,
                "onboard": 0
            },
            {
                "label": "KEK Item Tolerance",
                "type": "Link",
                "link_to": "KEK Item Tolerance",
                "link_type": "DocType",
                "hidden": 0,
                "onboard": 0
            },
            {
                "label": "KEK Company Profile",
                "type": "Link",
                "link_to": "KEK Company Profile",
                "link_type": "DocType",
                "hidden": 0,
                "onboard": 0
            }
        ]
    })
    
    doc.insert()
    frappe.db.commit()
    print(f"Successfully created standard KEK IT Inventory Workspace.")

if __name__ == "__main__":
    main()
