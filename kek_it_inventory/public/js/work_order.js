// Copyright (c) 2026, Singlecore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Order', {
	onload: function(frm) {
		// Event delegation for Complete Stage buttons (bound to form wrapper to prevent duplicates or memory leaks)
		$(frm.wrapper).off('click', '.btn-complete-stage').on('click', '.btn-complete-stage', function() {
			let wo_to_complete = $(this).attr('data-wo');
			let target_qty = flt($(this).attr('data-target'));
			let item_name = $(this).attr('data-item-name');

			frappe.prompt(
				[
					{
						label: __('Kuantitas Hasil Produksi'),
						fieldname: 'actual_qty',
						fieldtype: 'Float',
						default: target_qty,
						reqd: 1,
						description: __('Kuantitas yang berhasil diproduksi pada tahap ini.')
					}
				],
				function(values) {
					if (values.actual_qty <= 0) {
						frappe.msgprint(__('Kuantitas harus lebih besar dari 0.'));
						return;
					}
					if (values.actual_qty > target_qty) {
						frappe.msgprint(__('Kuantitas aktual tidak boleh melebihi kuantitas target ({0}).', [target_qty]));
						return;
					}

					frappe.call({
						method: 'kek_it_inventory.kek_it_inventory.services.manufacture_service.complete_production_stage',
						args: {
							work_order_name: wo_to_complete,
							actual_qty: values.actual_qty
						},
						callback: function(res) {
							if (res.message && res.message.status === "Success") {
								frappe.show_alert({
									message: __('Tahapan selesai! Stock Entry {0} disubmit.', [res.message.stock_entry]),
									indicator: 'green'
								});
								frm.reload_doc();
							}
						}
					});
				},
				__('Konfirmasi Selesai Tahap: {0}', [item_name]),
				__('Submit Hasil')
			);
		});

		// Event delegation untuk cetak per baris tahapan
		$(frm.wrapper).off('click', '.btn-print-stage-bom').on('click', '.btn-print-stage-bom', function() {
			let bom_no = $(this).attr('data-bom');
			let target_qty = flt($(this).attr('data-target'));
			let stage_name = $(this).attr('data-item-name');
			let wip_wh = $(this).attr('data-wip-wh');
			let work_order_no = $(this).attr('data-wo');
			if (bom_no) {
				cetak_bahan_per_tahap(bom_no, target_qty, stage_name, wip_wh, work_order_no);
			} else {
				frappe.msgprint(__('BOM tidak ditemukan untuk tahap ini.'));
			}
		});

		// Event delegation untuk cetak gabungan keseluruhan
		$(frm.wrapper).off('click', '#btn-print-all-stages-bom').on('click', '#btn-print-all-stages-bom', function() {
			let work_order_name = $(this).attr('data-main-wo');
			cetak_seluruh_bahan_gabungan(work_order_name);
		});
	},
	
	refresh: function(frm) {
		// If it's a sub-Work Order, link back to parent and do not render the dashboard
		if (frm.doc.parent_work_order) {
			frm.set_intro(__('Ini adalah Sub-Work Order pendukung. Klik di sini untuk kembali ke <a href="/app/work-order/{0}">Work Order Utama ({0})</a>.', [frm.doc.parent_work_order]), 'blue');
			return;
		}

		// Render the dashboard only for saved draft and submitted main Work Orders
		if (frm.doc.docstatus < 2 && !frm.is_new()) {
			render_multi_stage_dashboard(frm);
		}
	}
});

function render_multi_stage_dashboard(frm) {
	// Call backend to get production stages status
	frappe.call({
		method: 'kek_it_inventory.kek_it_inventory.services.manufacture_service.get_production_stages',
		args: {
			work_order_name: frm.doc.name
		},
		callback: function(r) {
			if (!r.message) return;
			let stages = r.message;

			let completed_count = 0;
			let active_stage_idx = -1;

			// Determine which stage is currently active
			for (let i = 0; i < stages.length; i++) {
				if (stages[i].status === "Completed") {
					completed_count++;
				} else if (active_stage_idx === -1) {
					active_stage_idx = i;
				}
			}

			// Render Draft Mode Banner if applicable
			let banner_html = "";
			if (frm.doc.docstatus === 0) {
				banner_html = `
					<div class="alert alert-warning" style="margin-bottom: 20px; font-size: 13px; border-radius: 6px; padding: 10px 15px; border-left: 4px solid #F59E0B; background-color: #FEF3C7; color: #92400E;">
						⚠️ <strong>Draft Mode:</strong> Silakan <strong>Submit</strong> Work Order ini terlebih dahulu untuk mengaktifkan tombol aksi pengerjaan tahapan dan otomatisasi mutasi stok.
					</div>
				`;
			}

			let hud_html = `
				<div class="multi-stage-container" style="border: 1px solid #d1d8dd; border-radius: 8px; padding: 20px; background-color: #ffffff; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: left;">
					<h4 style="margin-top: 0; margin-bottom: 20px; color: #1F2937; font-weight: 600; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
						<span style="display: flex; align-items: center; gap: 8px;">
							<span class="indicator-pill blue" style="width: 10px; height: 10px; border-radius: 50%; background-color: #2563EB; display: inline-block;"></span>
							Dashboard Produksi Multi-Stage (BOM Multi)
						</span>
						<button id="btn-print-all-stages-bom" data-main-wo="${frm.doc.name}" class="btn btn-primary btn-xs" style="font-weight: 500; font-size: 12px; padding: 4px 10px;">
							🖨️ Cetak Semua Bahan (Tahap 1-${stages.length})
						</button>
					</h4>
					${banner_html}
					<div class="stepper-wrapper" style="display: flex; justify-content: space-between; position: relative; margin-bottom: 30px;">
						<!-- Stepper Line -->
						<div class="stepper-line" style="position: absolute; top: 15px; left: 5%; right: 5%; height: 4px; background-color: #E5E7EB; z-index: 1;"></div>
						<div class="stepper-line-progress" id="stepper-progress-line" style="position: absolute; top: 15px; left: 5%; width: 0%; height: 4px; background-color: #10B981; z-index: 2; transition: width 0.4s ease;"></div>
					</div>
					<div class="stages-table-container">
						<table class="table table-bordered" style="margin-bottom: 0; width: 100%;">
							<thead>
								<tr style="background-color: #F9FAFB;">
									<th style="width: 80px; text-align: center; color: #4B5563; font-weight: 500;">Tahap</th>
									<th style="color: #4B5563; font-weight: 500;">Item / Proses</th>
									<th style="width: 180px; color: #4B5563; font-weight: 500;">Gudang WIP</th>
									<th style="width: 150px; color: #4B5563; font-weight: 500;">Work Order No</th>
									<th style="width: 120px; text-align: center; color: #4B5563; font-weight: 500;">Qty Target</th>
									<th style="width: 120px; text-align: center; color: #4B5563; font-weight: 500;">Qty Aktual</th>
									<th style="width: 130px; text-align: center; color: #4B5563; font-weight: 500;">Status</th>
									<th style="width: 180px; text-align: center; color: #4B5563; font-weight: 500;">Aksi</th>
								</tr>
							</thead>
							<tbody id="stages-table-body"></tbody>
						</table>
					</div>
				</div>
			`;

			frm.dashboard.clear_headline();
			frm.dashboard.set_headline(hud_html);

			// Render Stepper and Table rows using global jQuery selectors to avoid wrapper reference issues
			let $stepper = $('.stepper-wrapper');
			let $table_body = $('#stages-table-body');
			
			// Clear existing stepper nodes (except lines)
			$stepper.find('.step-node').remove();
			$table_body.empty();

			// Update Stepper Progress Line Width
			let progress_pct = stages.length > 1 ? (completed_count / (stages.length - 1)) * 90 : 0;
			if (progress_pct > 90) progress_pct = 90;
			$('#stepper-progress-line').css('width', progress_pct + '%');

			// Loop through stages to build UI
			stages.forEach(function(s, idx) {
				// 1. Render Stepper Nodes
				let is_completed = s.status === "Completed";
				let is_active = idx === active_stage_idx;
				
				let node_color = "#E5E7EB"; // Pending
				let text_weight = "normal";
				let text_color = "#9CA3AF";
				let step_icon = idx + 1;

				if (is_completed) {
					node_color = "#10B981"; // Success green
					text_weight = "600";
					text_color = "#10B981";
					step_icon = "✓";
				} else if (is_active && frm.doc.docstatus === 1) {
					node_color = "#2563EB"; // Active blue
					text_weight = "600";
					text_color = "#2563EB";
				}

				let $step_node = $(`
					<div class="step-node" style="display: flex; flex-direction: column; align-items: center; width: 80px; z-index: 3;">
						<div class="step-circle" style="width: 32px; height: 32px; border-radius: 50%; background-color: ${node_color}; color: #ffffff; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.3s ease;">
							${step_icon}
						</div>
						<div class="step-label" style="margin-top: 8px; font-size: 11px; text-align: center; font-weight: ${text_weight}; color: ${text_color}; line-height: 1.2;">
							${s.item_name}
						</div>
					</div>
				`);
				$stepper.append($step_node);

				// 2. Render Table Rows
				let status_badge_color = "gray";
				if (s.status === "Completed") status_badge_color = "green";
				else if (s.status === "In Progress") status_badge_color = "orange";
				else if (is_active && frm.doc.docstatus === 1) status_badge_color = "blue";

				let action_btns = `<button class="btn btn-default btn-xs btn-print-stage-bom" data-wo="${s.work_order || ''}" data-bom="${s.bom_no || ''}" data-target="${s.target_qty || 0}" data-item-name="${s.item_name}" data-wip-wh="${s.wip_warehouse || ''}" style="margin-right: 4px;" title="Cetak Kebutuhan Bahan">🖨️ Cetak</button>`;
				if (frm.doc.docstatus === 0) {
					action_btns += `<button class="btn btn-default btn-xs" disabled style="opacity: 0.5; cursor: not-allowed;">Draft Mode</button>`;
				} else if (is_active && frm.doc.status !== "Stopped" && frm.doc.status !== "Completed") {
					action_btns += `<button class="btn btn-primary btn-xs btn-complete-stage" data-wo="${s.work_order}" data-idx="${s.stage_index}" data-target="${s.target_qty}" data-item-name="${s.item_name}" style="background-color: #2563EB; border-color: #2563EB; font-weight: 500; padding: 4px 10px;">Complete</button>`;
				} else {
					action_btns += `<button class="btn btn-default btn-xs" disabled style="opacity: 0.5;">Waiting</button>`;
				}

				let row_style = (is_active && frm.doc.docstatus === 1) ? "background-color: #EFF6FF;" : "";

				let $row = $(`
					<tr style="${row_style}">
						<td style="text-align: center; vertical-align: middle; font-weight: bold; color: #4B5563;">${idx + 1}</td>
						<td style="vertical-align: middle;">
							<div style="font-weight: 600; color: #1F2937;">${s.item_name}</div>
							<div style="font-size: 11px; color: #6B7280;">Code: ${s.item_code}</div>
						</td>
						<td style="vertical-align: middle; color: #374151;">${s.wip_warehouse || '-'}</td>
						<td style="vertical-align: middle; font-family: monospace;">
							${s.work_order ? `<a href="/app/work-order/${s.work_order}">${s.work_order}</a>` : '-'}
						</td>
						<td style="text-align: center; vertical-align: middle; font-weight: 600; color: #1F2937;">${s.target_qty}</td>
						<td style="text-align: center; vertical-align: middle; font-weight: 600; color: #10B981;">${s.produced_qty || '-'}</td>
						<td style="text-align: center; vertical-align: middle;">
							<span class="indicator-pill ${status_badge_color}" style="padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 500;">
								${s.status}
							</span>
						</td>
						<td style="text-align: center; vertical-align: middle;">${action_btns}</td>
					</tr>
				`);
				$table_body.append($row);
			});
		}
	});
}

function cetak_bahan_per_tahap(bom_no, target_qty, stage_name, wip_wh, work_order_no) {
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'BOM',
			name: bom_no
		},
		callback: function(r) {
			if (!r.message) return;
			let bom = r.message;
			let items_html = bom.items.map(item => {
				let req_qty = (flt(item.qty) / flt(bom.quantity)) * target_qty;
				return `
					<tr>
						<td style="border: 1px solid #ddd; padding: 8px;">${item.item_code}</td>
						<td style="border: 1px solid #ddd; padding: 8px;">${item.item_name || item.item_code}</td>
						<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">${frappe.format(req_qty, {fieldtype: 'Float'})} ${item.uom}</td>
						<td style="border: 1px solid #ddd; padding: 8px;"></td>
						<td style="border: 1px solid #ddd; padding: 8px;"></td>
					</tr>
				`;
			}).join('');

			let print_html = `
				<html>
				<head>
					<title>Cetak Bahan: ${stage_name}</title>
					<style>
						body { font-family: sans-serif; padding: 20px; }
						table { width: 100%; border-collapse: collapse; margin-top: 20px; }
						th { background-color: #f2f2f2; }
						th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
					</style>
				</head>
				<body>
					<h2>Kebutuhan Bahan Baku Per Tahap</h2>
					<p><b>Work Order No:</b> ${work_order_no || '-'}</p>
					<p><b>Tahap / Item:</b> ${stage_name}</p>
					<p><b>BOM No:</b> ${bom_no}</p>
					<p><b>Qty Target:</b> ${frappe.format(target_qty, {fieldtype: 'Float'})}</p>
					<p><b>Gudang WIP:</b> ${wip_wh || '-'}</p>
					<table>
						<thead>
							<tr>
								<th>Kode Item</th>
								<th>Nama Item</th>
								<th>Qty Dibutuhkan</th>
								<th style="width: 120px;">QTY Receive</th>
								<th style="width: 150px;">Ket</th>
							</tr>
						</thead>
						<tbody>
							${items_html}
						</tbody>
					</table>
					<script>
						window.onload = function() { window.print(); }
					</script>
				</body>
				</html>
			`;
			let w = window.open();
			w.document.write(print_html);
			w.document.close();
			w.focus();
			w.print();
		}
	});
}

function cetak_seluruh_bahan_gabungan(work_order_name) {
	frappe.call({
		method: 'kek_it_inventory.kek_it_inventory.services.manufacture_service.get_production_stages',
		args: {
			work_order_name: work_order_name
		},
		callback: function(r) {
			if (!r.message) return;
			let stages = r.message;
			
			let promises = stages.filter(s => s.bom_no).map(s => {
				return new Promise((resolve) => {
					frappe.call({
						method: 'frappe.client.get',
						args: {
							doctype: 'BOM',
							name: s.bom_no
						},
						callback: function(res) {
							if (res.message) {
								resolve({ stage: s, bom: res.message });
							} else {
								resolve(null);
							}
						}
					});
				});
			});

			Promise.all(promises).then(results => {
				let consolidated = {};
				
				results.forEach(res => {
					if (!res) return;
					let target_qty = res.stage.target_qty;
					let bom = res.bom;
					bom.items.forEach(item => {
						let req_qty = (flt(item.qty) / flt(bom.quantity)) * target_qty;
						if (consolidated[item.item_code]) {
							consolidated[item.item_code].qty += req_qty;
						} else {
							consolidated[item.item_code] = {
								item_code: item.item_code,
								item_name: item.item_name || item.item_code,
								qty: req_qty,
								uom: item.uom
							};
						}
					});
				});

				let items_html = Object.values(consolidated).map(item => `
					<tr>
						<td style="border: 1px solid #ddd; padding: 8px;">${item.item_code}</td>
						<td style="border: 1px solid #ddd; padding: 8px;">${item.item_name}</td>
						<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">${frappe.format(item.qty, {fieldtype: 'Float'})} ${item.uom}</td>
						<td style="border: 1px solid #ddd; padding: 8px;"></td>
						<td style="border: 1px solid #ddd; padding: 8px;"></td>
					</tr>
				`).join('');

				let print_html = `
					<html>
					<head>
						<title>Cetak Semua Bahan: ${work_order_name}</title>
						<style>
							body { font-family: sans-serif; padding: 20px; }
							table { width: 100%; border-collapse: collapse; margin-top: 20px; }
							th { background-color: #f2f2f2; }
							th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
						</style>
					</head>
					<body>
						<h2>Gabungan Kebutuhan Bahan Baku (Tahap 1-${stages.length})</h2>
						<p><b>Work Order Utama:</b> ${work_order_name}</p>
						<table>
							<thead>
								<tr>
									<th>Kode Item</th>
									<th>Nama Item</th>
									<th>Total Qty</th>
									<th style="width: 120px;">QTY Receive</th>
									<th style="width: 150px;">Ket</th>
								</tr>
							</thead>
							<tbody>
								${items_html}
							</tbody>
						</table>
						<script>
							window.onload = function() { window.print(); }
						</script>
					</body>
					</html>
				`;
				let w = window.open();
				w.document.write(print_html);
				w.document.close();
				w.focus();
				w.print();
			});
		}
	});
}
