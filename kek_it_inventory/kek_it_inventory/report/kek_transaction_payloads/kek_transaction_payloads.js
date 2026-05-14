frappe.query_reports["KEK Transaction Payloads"] = {
	"filters": [
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nQUEUED\nSENT\nFAILED",
			"default": ""
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "status") {
			if (data.status == "FAILED") {
				value = `<span style='color:red; font-weight:bold;'>${value}</span>`;
			} else if (data.status == "SENT") {
				value = `<span style='color:green;'>${value}</span>`;
			}
		}

		return value;
	},
	"onload": function(report) {
		report.page.add_inner_button(__("Refresh Data"), function() {
			report.refresh();
		});
	}
};
