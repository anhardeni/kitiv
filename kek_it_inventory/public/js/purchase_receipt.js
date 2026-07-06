// Copyright (c) 2026, Singlecore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Receipt', {
	refresh: function(frm) {
		// Set dynamic form indicator/alert based on KEK status
		if (frm.doc.docstatus === 1) { // Submitted
			if (frm.doc.kek_status === 'Validated' || frm.doc.kek_status === 'ACKNOWLEDGED') {
				frm.set_intro(__('Dokumen PPKEK ter-validasi (Green). Nomor PPKEK: {0}', [frm.doc.nomor_ppkek || '-']), 'green');
			} else if (frm.doc.kek_status === 'BYPASSED') {
				frm.set_intro(__('Dokumen ini melewati pemeriksaan pabean (Emergency Bypass / Yellow). Alasan: {0}', [frm.doc.bypass_reason || '-']), 'orange');
			} else if (frm.doc.kek_status === 'MISMATCH') {
				frm.set_intro(__('PERINGATAN: Terjadi perbedaan jumlah barang atau item (Mismatch / Red) antara ERPNext dan Bea Cukai.'), 'red');
			} else if (frm.doc.kek_status === 'FAILED') {
				frm.set_intro(__('Gagal mengirim data ke KEK Bea Cukai (Red): {0}', [frm.doc.kek_error || 'Unknown Error']), 'red');
			} else if (frm.doc.kek_status === 'PENDING' || frm.doc.kek_status === 'QUEUED' || frm.doc.kek_status === 'SENT') {
				frm.set_intro(__('Dokumen pabean PPKEK dalam antrean/sedang diproses (Pending / Orange).'), 'orange');
			} else {
				frm.set_intro(__('Dokumen KEK belum diproses.'), 'orange');
			}

			// Add action buttons
			// 1. Kirim/Retry KEK (if status is FAILED or empty)
			if (!frm.doc.kek_status || frm.doc.kek_status === 'FAILED') {
				frm.add_custom_button(__('Kirim KEK'), function() {
					frm.set_working(true);
					frappe.call({
						method: 'kek_it_inventory.kek_it_inventory.services.kek_service.retry_kek',
						args: {
							docname: frm.doc.name,
							doctype: frm.doc.doctype
						},
						callback: function(r) {
							frm.reload_doc();
							frappe.show_alert({
								message: __('Mencoba mengirim transaksi ke KEK...'),
								indicator: 'orange'
							});
						},
						always: function() {
							frm.set_working(false);
						}
					});
				}, __('Actions'));
			}

			// 2. Lihat Transaksi KEK (if kek_transaction is set)
			if (frm.doc.kek_transaction) {
				frm.add_custom_button(__('Lihat Transaksi KEK'), function() {
					frappe.set_route('Form', 'KEK Inventory Transaction', frm.doc.kek_transaction);
				}, __('Actions'));
			}

			// 3. Unduh XLS Barang (For manual upload to Customs portal)
			frm.add_custom_button(__('Unduh XLS Barang'), function() {
				window.open('/api/method/kek_it_inventory.kek_it_inventory.services.kek_service.download_customs_xls'
					+ '?doctype=' + encodeURIComponent(frm.doc.doctype)
					+ '&docname=' + encodeURIComponent(frm.doc.name));
			}, __('Actions'));
		}

		// Enforce bypass fields permissions
		let is_manager = frappe.user.has_role("KEK Manager") || frappe.user.has_role("System Manager");
		frm.toggle_enable("bypass_kek_validation", is_manager && frm.doc.docstatus === 0);
		frm.toggle_enable("bypass_reason", is_manager && frm.doc.bypass_kek_validation && frm.doc.docstatus === 0);
		frm.toggle_reqd("bypass_reason", !!frm.doc.bypass_kek_validation);
	},
	bypass_kek_validation: function(frm) {
		let is_manager = frappe.user.has_role("KEK Manager") || frappe.user.has_role("System Manager");
		frm.toggle_enable("bypass_reason", is_manager && frm.doc.bypass_kek_validation && frm.doc.docstatus === 0);
		frm.toggle_reqd("bypass_reason", !!frm.doc.bypass_kek_validation);
	}
});
