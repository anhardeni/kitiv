frappe.ui.form.on('Purchase Order', {
	refresh: function(frm) {
		// Set dynamic form indicator/alert based on KEK status
		if (frm.doc.docstatus === 1) { // Submitted
			if (frm.doc.kek_status === 'Validated') {
				frm.set_intro(__('Dokumen PPKEK ter-validasi (Green). Nomor PPKEK: {0}', [frm.doc.nomor_ppkek || '-']), 'green');
			} else if (frm.doc.kek_status === 'BYPASSED') {
				frm.set_intro(__('Dokumen ini melewati pemeriksaan pabean (Emergency Bypass / Yellow). Alasan: {0}', [frm.doc.bypass_reason || '-']), 'orange');
			} else if (frm.doc.kek_status === 'MISMATCH') {
				frm.set_intro(__('PERINGATAN: Terjadi perbedaan jumlah barang atau item (Mismatch / Red) antara ERPNext dan Bea Cukai.'), 'red');
			} else if (frm.doc.kek_status === 'FAILED') {
				frm.set_intro(__('Gagal memproses pabean KEK (Red): {0}', [frm.doc.kek_error || 'Unknown Error']), 'red');
			} else if (frm.doc.kek_status === 'PENDING') {
				frm.set_intro(__('Dokumen pabean PPKEK sedang diverifikasi oleh Bea Cukai (Pending / Orange).'), 'orange');
			} else {
				frm.set_intro(__('Dokumen KEK dalam proses antrean.'), 'orange');
			}

			// Add action buttons
			// 1. Kirim/Retry KEK (if status is FAILED or empty)
			if (!frm.doc.kek_status || frm.doc.kek_status === 'FAILED' || frm.doc.kek_status === 'MISMATCH') {
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

			// 3. Input Nomor PPKEK (Manual verification from customs web portal)
			if (frm.doc.kek_status !== 'Validated' && (frappe.user.has_role('KEK Manager') || frappe.user.has_role('System Manager'))) {
				frm.add_custom_button(__('Input Nomor PPKEK'), function() {
					frappe.prompt([
						{
							label: 'Nomor PPKEK',
							fieldname: 'nomor_ppkek',
							fieldtype: 'Data',
							reqd: 1
						}
					], function(values){
						frappe.call({
							method: 'kek_it_inventory.kek_it_inventory.services.kek_service.manual_validate_ppkek',
							args: {
								doctype: frm.doc.doctype,
								docname: frm.doc.name,
								nomor_ppkek: values.nomor_ppkek
							},
							callback: function() {
								frm.reload_doc();
								frappe.show_alert({
									message: __('Berhasil memverifikasi dokumen PPKEK secara manual.'),
									indicator: 'green'
								});
							}
						});
					}, __('Verifikasi PPKEK'), __('Simpan'));
				}, __('Actions'));
			}

			// 4. Unduh XLS Barang (For manual upload to Customs portal)
			frm.add_custom_button(__('Unduh XLS Barang'), function() {
				window.open('/api/method/kek_it_inventory.kek_it_inventory.services.kek_service.download_customs_xls'
					+ '?doctype=' + encodeURIComponent(frm.doc.doctype)
					+ '&docname=' + encodeURIComponent(frm.doc.name));
			}, __('Actions'));
		}
	}
});
