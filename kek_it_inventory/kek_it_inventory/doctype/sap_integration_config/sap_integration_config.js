// -*- coding: utf-8 -*-
frappe.ui.form.on('SAP Integration Config', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            
            // 1. TOMBOL UJI DRY-RUN
            frm.page.add_inner_button(__('Uji Payload (Dry-Run)'), function() {
                if (!frm.doc.sap_sample_payload) {
                    frappe.msgprint(__('Silakan tempel sampel JSON dari SAP pada kolom Sample Payload for Testing.'));
                    return;
                }
                
                frappe.call({
                    method: 'kek_it_inventory.kek_it_inventory.sap_connector.validator.run_automated_mapping_check',
                    args: { payload: frm.doc.sap_sample_payload },
                    freeze: true,
                    freeze_message: __('Menjalankan Uji Coba Sandbox...'),
                    callback: function(r) {
                        if (r.message && r.message.html_report) {
                            let dialog = new frappe.ui.Dialog({
                                title: __('Hasil Uji Coba Data (Dry-Run Report)'),
                                size: 'large',
                                fields: [{ fieldname: 'report_html', fieldtype: 'HTML', options: r.message.html_report }]
                            });
                            dialog.show();
                        }
                    }
                });
            }, __('Aksi Integrasi SAP'));

            // 2. TOMBOL REPARASI MAPPING
            frm.page.add_inner_button(__('Reparasi Otomatis Mapping'), function() {
                if (!frm.doc.sap_sample_payload) {
                    frappe.msgprint(__('Tempel sampel JSON SAP terlebih dahulu.'));
                    return;
                }

                frappe.confirm(
                    __('Apakah Anda yakin ingin mereparasi otomatis kolom tabel pemetaan berdasarkan JSON sampel saat ini?'),
                    function() {
                        frappe.call({
                            method: 'kek_it_inventory.kek_it_inventory.sap_connector.validator.auto_repair_sap_mappings',
                            args: {
                                doc_name: frm.doc.name,
                                payload: frm.doc.sap_sample_payload
                            },
                            freeze: true,
                            freeze_message: __('Mereparasi Child Table...'),
                            callback: function(r) {
                                if (r.message && r.message.status === 'Success') {
                                    frappe.show_alert({ message: __(r.message.message), indicator: 'green' });
                                    frm.reload_doc(); 
                                }
                            }
                        });
                    }
                );
            }, __('Aksi Integrasi SAP'));
        }
    }
});
