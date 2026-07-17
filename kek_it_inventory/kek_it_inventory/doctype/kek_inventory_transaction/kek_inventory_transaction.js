// Copyright (c) 2026, Singlecore and contributors
// For license information, please see license.txt

frappe.ui.form.on('KEK Inventory Transaction', {
	refresh: function(frm) {
		// Render premium HUD
		let status = frm.doc.status;
		let indicator_bg = '#f59e0b';
		let status_text_color = '#d97706';
		let status_label = __('Antrean (Queued)');
		
		let step1_bg = '#fef3c7', step1_fg = '#d97706', step1_border = '#f59e0b';
		let step2_bg = '#f3f4f6', step2_fg = '#9ca3af', step2_border = '#e5e7eb';
		let step3_bg = '#f3f4f6', step3_fg = '#9ca3af', step3_border = '#e5e7eb';
		let line1_bg = '#e5e7eb', line2_bg = '#e5e7eb';

		if (status === 'SENT') {
			indicator_bg = '#3b82f6';
			status_text_color = '#2563eb';
			status_label = __('Terkirim (Sent)');
			step1_bg = '#d1fae5'; step1_fg = '#059669'; step1_border = '#34d399';
			step2_bg = '#dbeafe'; step2_fg = '#2563eb'; step2_border = '#3b82f6';
			line1_bg = '#3b82f6';
		} else if (status === 'ACKNOWLEDGED') {
			indicator_bg = '#10b981';
			status_text_color = '#059669';
			status_label = __('Diterima (Acknowledged)');
			step1_bg = '#d1fae5'; step1_fg = '#059669'; step1_border = '#34d399';
			step2_bg = '#d1fae5'; step2_fg = '#059669'; step2_border = '#34d399';
			step3_bg = '#d1fae5'; step3_fg = '#059669'; step3_border = '#34d399';
			line1_bg = '#10b981'; line2_bg = '#10b981';
		} else if (status === 'FAILED') {
			indicator_bg = '#ef4444';
			status_text_color = '#dc2626';
			status_label = __('Gagal (Failed)');
			step1_bg = '#d1fae5'; step1_fg = '#059669'; step1_border = '#34d399';
			step2_bg = '#fee2e2'; step2_fg = '#dc2626'; step2_border = '#ef4444';
			line1_bg = '#ef4444';
		}

		let error_section = '';
		if (status === 'FAILED' && frm.doc.response_payload) {
			try {
				let res = JSON.parse(frm.doc.response_payload);
				let msg = res.message || (res.data && res.data.resultDataTransaksi && res.data.resultDataTransaksi[0] && res.data.resultDataTransaksi[0].keterangan) || __('Unknown API error.');
				error_section = `
					<div style="margin-top: 15px; padding: 12px; background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; border-radius: 4px; color: #b91c1c; font-size: 13px; font-weight: 500;">
						❌ <b>Respon Error Bea Cukai:</b> ${msg}
					</div>
				`;
			} catch(e) {}
		}

		let hud_html = `
			<div class="kek-status-hud" style="
				background: linear-gradient(135deg, var(--card-bg, #ffffff), var(--bg-color, #f9fafb));
				border: 1px solid var(--border-color, #e5e7eb);
				border-radius: 12px;
				padding: 20px;
				margin-bottom: 20px;
				box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
			">
				<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
					<div style="display: flex; flex-direction: column; gap: 4px;">
						<span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; font-weight: 600; color: var(--text-muted, #6b7280);">SINSW Integration Hub</span>
						<div style="display: flex; align-items: center; gap: 8px;">
							<span class="indicator-pill" style="
								width: 10px;
								height: 10px;
								border-radius: 50%;
								background-color: ${indicator_bg};
								box-shadow: 0 0 8px ${indicator_bg};
								display: inline-block;
							"></span>
							<span style="font-size: 18px; font-weight: 700; color: ${status_text_color};">${status_label}</span>
						</div>
					</div>
					
					<!-- Stepper -->
					<div style="display: flex; align-items: center; gap: 8px;">
						<div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
							<div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; background: ${step1_bg}; color: ${step1_fg}; border: 1.5px solid ${step1_border};">1</div>
							<span style="font-size: 10px; font-weight: 600; color: var(--text-color, #1f2937);">Queued</span>
						</div>
						<div style="width: 40px; height: 2px; background: ${line1_bg}; margin-top: -14px;"></div>
						<div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
							<div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; background: ${step2_bg}; color: ${step2_fg}; border: 1.5px solid ${step2_border};">2</div>
							<span style="font-size: 10px; font-weight: 600; color: var(--text-color, #1f2937);">Sent</span>
						</div>
						<div style="width: 40px; height: 2px; background: ${line2_bg}; margin-top: -14px;"></div>
						<div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
							<div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; background: ${step3_bg}; color: ${step3_fg}; border: 1.5px solid ${step3_border};">3</div>
							<span style="font-size: 10px; font-weight: 600; color: var(--text-color, #1f2937);">ACK</span>
						</div>
					</div>
				</div>
				${error_section}
			</div>
		`;
		
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(hud_html);

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

		// 2. Tombol [ Kirim ] (Prominent)
		if (frm.doc.status !== 'ACKNOWLEDGED') {
			frm.add_custom_button(__('Kirim Ke Bea Cukai'), function() {
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
			});
		}

		// 3. Tombol [ Retry ] (Hanya muncul jika status FAILED - Prominent)
		if (frm.doc.status === 'FAILED') {
			frm.add_custom_button(__('Retry Kirim'), function() {
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
			});
		}

		// 4. Tombol [ Lihat Payload JSON ] (Prominent)
		if (frm.doc.request_payload) {
			frm.add_custom_button(__('Lihat Payload JSON'), function() {
				let d = new frappe.ui.Dialog({
					title: __('Request Payload JSON'),
					size: 'large',
					fields: [
						{
							fieldname: 'payload',
							fieldtype: 'Code',
							label: __('Request JSON Data'),
							options: 'JSON',
							read_only: 1,
							default: frm.doc.request_payload
						}
					]
				});
				d.show();
			});
		}

		// 5. Tombol [ Lihat Respon API ] (Prominent)
		if (frm.doc.response_payload) {
			frm.add_custom_button(__('Lihat Respon API'), function() {
				let d = new frappe.ui.Dialog({
					title: __('Response Payload JSON'),
					size: 'large',
					fields: [
						{
							fieldname: 'payload',
							fieldtype: 'Code',
							label: __('Response JSON Data'),
							options: 'JSON',
							read_only: 1,
							default: frm.doc.response_payload
						}
					]
				});
				d.show();
			});
		}
	}
});
