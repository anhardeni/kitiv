// Copyright (c) 2026, Singlecore and contributors
// For license information, please see license.txt

frappe.ui.form.on('KEK Inventory Transaction', {
	refresh: function(frm) {
		// Set dynamic form indicator based on status
		if (frm.doc.status === 'SENT') {
			frm.set_intro(__('Transaksi ini telah berhasil dikirim ke portal SINSW.'), 'green');
		} else if (frm.doc.status === 'ACKNOWLEDGED') {
			frm.set_intro(__('Transaksi telah diterima dan di-acknowledge oleh sistem Bea Cukai.'), 'blue');
		} else if (frm.doc.status === 'FAILED') {
			frm.set_intro(__('Terjadi kegagalan pengiriman ke Bea Cukai. Harap periksa respon pabean.'), 'red');
		} else {
			frm.set_intro(__('Transaksi ini dalam status antrean (Draft/Queued) dan siap divalidasi atau dikirim.'), 'orange');
		}

		// 1. Tombol [ Validate ]
		frm.add_custom_button(__('Validate'), function() {
			frappe.call({
				method: 'kek_it_inventory.kek_it_inventory.services.kek_service.validate_only',
				args: {
					docname: frm.doc.name
				},
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: __('Validation Success: ') + r.message,
							indicator: 'green'
						});
					}
				}
			});
		}, __('Actions'));

		// 2. Tombol [ Kirim ]
		frm.add_custom_button(__('Kirim'), function() {
			frappe.confirm(__('Apakah Anda yakin ingin mengirim transaksi ini langsung ke Bea Cukai / SINSW?'), function() {
				frm.set_working(true);
				frappe.call({
					method: 'kek_it_inventory.kek_it_inventory.api.poster.post_transaction',
					args: {
						docname: frm.doc.name
					},
					callback: function(r) {
						frm.reload_doc();
						frappe.show_alert({
							message: __('Transaksi KEK berhasil diposting.'),
							indicator: 'green'
						});
					},
					always: function() {
						frm.set_working(false);
					}
				});
			});
		}, __('Actions'));

		// 3. Tombol [ Retry ] (Hanya muncul jika status FAILED)
		if (frm.doc.status === 'FAILED') {
			frm.add_custom_button(__('Retry'), function() {
				frm.set_working(true);
				frappe.call({
					method: 'kek_it_inventory.kek_it_inventory.services.kek_service.retry_kek',
					args: {
						docname: frm.doc.name
					},
					callback: function(r) {
						frm.reload_doc();
						frappe.show_alert({
							message: __('Mencoba mengirim ulang transaksi KEK...'),
							indicator: 'orange'
						});
					},
					always: function() {
						frm.set_working(false);
					}
				});
			}, __('Actions'));
		}
	}
});
