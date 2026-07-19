# -*- coding: utf-8 -*-
import re
import frappe
from datetime import datetime
from frappe.utils import getdate, flt

def parse_sap_odata_date(date_string):
    """Mengubah format /Date(ms)/ SAP menjadi YYYY-MM-DD ERPNext"""
    if not date_string:
        return None
    if "Date" not in str(date_string):
        return str(getdate(date_string))
    try:
        match = re.search(r"/Date\((-?\d+)(?:[+-]\d+)?\)/", date_string)
        if match:
            timestamp_ms = int(match.group(1))
            dt_object = datetime.fromtimestamp(timestamp_ms / 1000.0)
            return dt_object.strftime("%Y-%m-%d")
    except Exception as e:
        frappe.log_error(title="SAP Date Parse Error", message=f"Input: {date_string} | {str(e)}")
    return None

def parse_sap_string_decimal(decimal_string):
    """Membersihkan format desimal lokal SAP menjadi Float standar"""
    if decimal_string is None:
        return 0.0
    clean_str = str(decimal_string).strip()
    if "," in clean_str and "." in clean_str:
        if clean_str.find(".") < clean_str.find(","):
            clean_str = clean_str.replace(".", "").replace(",", ".")
    elif "," in clean_str and "." not in clean_str:
        clean_str = clean_str.replace(",", ".")
    return flt(clean_str)