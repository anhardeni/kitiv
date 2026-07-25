frappe.ui.form.on('KEK API Credential', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Show Keys'), function() {
				frm.call({
					method: 'get_decrypted_keys',
					doc: frm.doc,
					freeze: true,
					freeze_message: __('Fetching API Keys...'),
					callback: function(r) {
						if (r.message) {
							let d = new frappe.ui.Dialog({
								title: __('API Keys'),
								fields: [
									{
										label: __('X-INSW-Key'),
										fieldname: 'x_insw_key',
										fieldtype: 'Data',
										read_only: 1,
										default: r.message.x_insw_key
									},
									{
										label: __('X-Unique-Key'),
										fieldname: 'x_unique_key',
										fieldtype: 'Data',
										read_only: 1,
										default: r.message.x_unique_key
									}
								],
								primary_action_label: __('Close'),
								primary_action(values) {
									d.hide();
								}
							});
							d.show();
						}
					}
				});
			});
		}

		if (frm.doc.environment === 'DUMMY' && !frm.is_new()) {
			frm.add_custom_button(__('Cleansing Data'), function() {
				frappe.confirm(
					__('Are you sure you want to clean all dummy data for this profile? This action is irreversible.'),
					function() {
						frm.call({
							method: 'clean_dummy_data',
							doc: frm.doc,
							freeze: true,
							freeze_message: __('Cleansing dummy data...'),
							callback: function(r) {
								if (!r.exc) {
									frappe.msgprint({
										title: __('Success'),
										indicator: 'green',
										message: r.message || __('Data cleansed successfully.')
									});
								}
							}
						});
					}
				);
			}).addClass('btn-danger');
		}
	}
});
