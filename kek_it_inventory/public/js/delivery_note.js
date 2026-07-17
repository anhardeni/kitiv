// Copyright (c) 2026, Singlecore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Note', {
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
				});
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

		// Set query filter for kek_transaction link field (1:N matching)
		frm.set_query("kek_transaction", function() {
			let parent_so = null;
			if (frm.doc.items && frm.doc.items.length) {
				for (let item of frm.doc.items) {
					if (item.against_sales_order) {
						parent_so = item.against_sales_order;
						break;
					}
				}
			}
			return {
				filters: {
					"erpnext_reference_doctype": "Sales Order",
					"erpnext_reference_name": parent_so || ""
				}
			};
		});

		// Synchronize custom_bc fields if nomor_ppkek / tanggal_ppkek are already populated via mapping
		if (frm.doc.nomor_ppkek && !frm.doc.custom_bc_registration_no) {
			frm.set_value("custom_bc_registration_no", frm.doc.nomor_ppkek);
		}
		if (frm.doc.tanggal_ppkek && !frm.doc.custom_bc_registration_date) {
			frm.set_value("custom_bc_registration_date", frm.doc.tanggal_ppkek);
		}

		// Auto-populate from parent SO if draft and empty
		if (frm.doc.docstatus === 0 && !frm.doc.nomor_ppkek) {
			let parent_so = null;
			if (frm.doc.items && frm.doc.items.length) {
				for (let item of frm.doc.items) {
					if (item.against_sales_order) {
						parent_so = item.against_sales_order;
						break;
					}
				}
			}
			if (parent_so) {
				frappe.db.get_value("Sales Order", parent_so, ["nomor_ppkek", "tanggal_ppkek", "kek_status"], (r) => {
					if (r && r.nomor_ppkek) {
						frm.set_value("nomor_ppkek", r.nomor_ppkek);
						frm.set_value("custom_bc_registration_no", r.nomor_ppkek);
						frm.set_value("tanggal_ppkek", r.tanggal_ppkek || "");
						frm.set_value("custom_bc_registration_date", r.tanggal_ppkek || "");
						if (r.kek_status) {
							frm.set_value("kek_status", r.kek_status);
						}
					}
				});
			}
		}
	},
	bypass_kek_validation: function(frm) {
		let is_manager = frappe.user.has_role("KEK Manager") || frappe.user.has_role("System Manager");
		frm.toggle_enable("bypass_reason", is_manager && frm.doc.bypass_kek_validation && frm.doc.docstatus === 0);
		frm.toggle_reqd("bypass_reason", !!frm.doc.bypass_kek_validation);
	},
	kek_transaction: function(frm) {
		if (frm.doc.kek_transaction) {
			frappe.db.get_value("KEK Inventory Transaction", frm.doc.kek_transaction, ["nomor_ppkek", "tanggal_ppkek"], (r) => {
				if (r) {
					frm.set_value("nomor_ppkek", r.nomor_ppkek || "");
					frm.set_value("custom_bc_registration_no", r.nomor_ppkek || "");
					frm.set_value("tanggal_ppkek", r.tanggal_ppkek || "");
					frm.set_value("custom_bc_registration_date", r.tanggal_ppkek || "");
				}
			});
		} else {
			frm.set_value("nomor_ppkek", "");
			frm.set_value("custom_bc_registration_no", "");
			frm.set_value("tanggal_ppkek", "");
			frm.set_value("custom_bc_registration_date", "");
		}
	},
	nomor_ppkek: function(frm) {
		if (frm.doc.nomor_ppkek !== frm.doc.custom_bc_registration_no) {
			frm.set_value("custom_bc_registration_no", frm.doc.nomor_ppkek);
		}
	},
	custom_bc_registration_no: function(frm) {
		if (frm.doc.custom_bc_registration_no !== frm.doc.nomor_ppkek) {
			frm.set_value("nomor_ppkek", frm.doc.custom_bc_registration_no);
		}
	},
	tanggal_ppkek: function(frm) {
		if (frm.doc.tanggal_ppkek !== frm.doc.custom_bc_registration_date) {
			frm.set_value("custom_bc_registration_date", frm.doc.tanggal_ppkek);
		}
	},
	custom_bc_registration_date: function(frm) {
		if (frm.doc.custom_bc_registration_date !== frm.doc.tanggal_ppkek) {
			frm.set_value("tanggal_ppkek", frm.doc.custom_bc_registration_date);
		}
	}
});
