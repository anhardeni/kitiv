# Graph Report - kek_it_inventory  (2026-07-19)

## Corpus Check
- 69 files · ~24,308 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 356 nodes · 386 edges · 45 communities (42 shown, 3 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 43 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a2fea6a8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 39|Community 39]]

## God Nodes (most connected - your core abstractions)
1. `post_transaction()` - 18 edges
2. `complete_production_stage()` - 11 edges
3. `get_production_stages()` - 10 edges
4. `TestManufactureService` - 10 edges
5. `create_kek_transaction()` - 9 edges
6. `process_sap_document_async()` - 8 edges
7. `TestSAPSync` - 8 edges
8. `seed_master_data()` - 7 edges
9. `post_transaction()` - 7 edges
10. `retry_kek()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `test_payload_structure_camelcase_and_nested()` --calls--> `post_transaction()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/api/test_poster.py → kek_it_inventory/kek_it_inventory/api/poster.py
- `seed_master_data()` --calls--> `setup_test_role_permissions()`  [INFERRED]
  kek_it_inventory/setup.py → kek_it_inventory/setup_role.py
- `seed_master_data()` --calls--> `setup_kek_manager_permissions()`  [INFERRED]
  kek_it_inventory/setup.py → kek_it_inventory/setup_role.py
- `seed_master_data()` --calls--> `setup_kek_user_permissions()`  [INFERRED]
  kek_it_inventory/setup.py → kek_it_inventory/setup_role.py
- `run_simulation()` --calls--> `update_ledger()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/sim_workflow.py → kek_it_inventory/kek_it_inventory/api/ledger.py

## Communities (45 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (38): create_kek_transaction(), Automatically creates a KEK Inventory Transaction from ERPNext documents 	with s, cancel_delivery_note_kek(), delete_delivery_note_kek(), on_delivery_note_submit(), process_delivery_note(), process_purchase_order(), process_purchase_receipt() (+30 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (18): Document, KEKAPICredential, KEKCompanyProfile, KEKComplianceArchive, KEKInventoryTransactionItem, KEKInventoryTransaction, KEKItemCustomsDoc, KEKItemMapping (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (22): adjust_subsequent_wos(), check_manufacture_permission(), complete_production_stage(), create_sub_work_orders(), ensure_custom_fields(), get_bom_hierarchy(), get_item_default_warehouse(), get_production_stages() (+14 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (10): download_customs_xls(), manual_validate_ppkek(), Memvalidasi status PPKEK secara manual oleh KEK Manager.     Mengubah status dok, Memvalidasi status PPKEK secara manual oleh KEK Manager.     Mengubah status dok, Generate XLS file containing item details structured for Bea Cukai KEK/CEISA upl, Generate XLS file containing item details structured for Bea Cukai KEK/CEISA upl, Memvalidasi status PPKEK secara manual oleh KEK Manager.     Mengubah status dok, Generate XLS file containing item details structured for Bea Cukai KEK/CEISA upl (+2 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (21): 1. Alur Inbound (Pemasukan), 1. Inbound Enforcement, 1. Indikator Status Visual (Status Banner), 2. Alur Outbound (Pengeluaran), 2. Emergency Bypass Policy, 2. Pesan Blokir yang Informatif & Solutif (Actionable Error Message), 3. Kendali Akses Kolom Bypass (Role-based Visibility), 3. Mismatch Status Triggers (+13 more)

### Community 5 - "Community 5"
Cohesion: 0.1
Nodes (17): bom_no, consolidated, item_name, items_html, promises, qty_actual_formatted, qty_target_formatted, stage_name (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (12): create_purchase_order(), create_sales_order(), normalize_uom(), process_sap_document_async(), process_sap_xls_chunked(), XLS Chunked Background Processor (Hybrid Method). 	Driven by the 'SAP PO Import, Scheduled OData pull: fetches POs from SAP S/4HANA and creates them in ERPNext., Whitelisted POST endpoint for SAP HANA to push PO/SO data. (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (16): get_unique_key(), post_transaction(), process_queue(), Finds all QUEUED transactions and attempts to post them., Finds all QUEUED transactions and attempts to post them., Retrieves the dynamic X-Unique-Key from SINSW., Propagates status back to the source ERPNext document., Translates technical/JSON error messages from Bea Cukai/SINSW API  	into clear, (+8 more)

### Community 8 - "Community 8"
Cohesion: 0.14
Nodes (14): Records movements into KEK Stock Ledger from a SENT transaction., update_ledger(), get_unique_key(), post_transaction(), process_queue(), Finds all QUEUED transactions and attempts to post them., Retrieves the dynamic X-Unique-Key from SINSW., Propagates status back to the source ERPNext document. (+6 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (15): 1.1 Penyesuaian Fisik & Selisih Pabean (Stock Opname & Adjustment), 1. Hakekat PPKEK: Unifikasi Dokumen Kepabeanan KEK, 2.1 Outbound: PPKEK Pengeluaran Sementara (ex-BC 2.6.1) - Kode `0407633`, 2.2 Inbound: PPKEK Pemasukan Kembali (ex-BC 2.6.2) - Kode `0407614`, 2. Alur Integrasi Spesifik Kasus Subkontrak (Maklon), 3.1 Penambahan Barang Lokal (TLDDP) di Lokasi Subkontraktor, 3.2 Manajemen Selisih BOM (BOM Discrepancy & Limit Toleransi), 3. Resolusi Masalah Operasional Tingkat Lanjut (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.2
Nodes (6): Fungsi ini berjalan otomatis sebelum setiap test dijalankan. 		FrappeTestCase ak, test_payload_structure_camelcase_and_nested(), TestPosterAPI, FrappeTestCase, TestKEKRefActivityCode, TestKEKRefCustomsDocument

### Community 11 - "Community 11"
Cohesion: 0.33
Nodes (7): create_kek_custom_fields(), Seed master reference data for KEK IT Inventory, setup_kek_manager_permissions(), setup_kek_user_permissions(), setup_test_role_permissions(), seed_doctype(), seed_master_data()

### Community 12 - "Community 12"
Cohesion: 0.22
Nodes (9): check_for_mismatch(), Membandingkan item & qty di KEK Inventory Transaction dengan source ERPNext docu, Membandingkan item & qty di KEK Inventory Transaction dengan source ERPNext docu, Job periodik untuk mengecek seluruh transaksi KEK 30 hari terakhir., Job periodik untuk mengecek seluruh transaksi KEK 30 hari terakhir., Membandingkan item & qty di KEK Inventory Transaction dengan source ERPNext docu, Job periodik untuk mengecek seluruh transaksi KEK 30 hari terakhir., run_mismatch_check_job() (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.25
Nodes (8): copy_parent_kek_details(), Menyalin nomor_ppkek dan kek_status dari PO/SO asal ke Receipt., Menyalin nomor_ppkek dan kek_status dari PO/SO asal ke Receipt., Memvalidasi status PPKEK sebelum receipt disubmit.     Harus berstatus 'ACKNOWLE, Memvalidasi status PPKEK sebelum receipt disubmit.     Harus berstatus 'ACKNOWLE, Menyalin nomor_ppkek dan tanggal_ppkek langsung dari parent document (PO/SO) ke, Memvalidasi status PPKEK sebelum receipt/Delivery Note disubmit.     Harus berst, validate_kek_submission()

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (6): code:bash (cd $PATH_TO_YOUR_BENCH), code:bash (cd apps/kek_it_inventory), Contributing, Installation, KEK IT Inventory, License

### Community 15 - "Community 15"
Cohesion: 0.33
Nodes (3): Immediately enqueue the chunked XLS processor after the job record is created., Reset progress fields if file changes and status is being re-queued, SAPPOImportJob

### Community 16 - "Community 16"
Cohesion: 0.4
Nodes (3): item_name, target_qty, wo_to_complete

### Community 17 - "Community 17"
Cohesion: 0.4
Nodes (4): daily_payload_summary(), get_failed_count(), Mengirim ringkasan transaksi kemarin ke tim operasional., Mengembalikan jumlah transaksi yang gagal untuk ditampilkan di badge desktop.

### Community 18 - "Community 18"
Cohesion: 0.7
Nodes (4): execute(), get_chart_data(), get_columns(), get_data()

### Community 19 - "Community 19"
Cohesion: 0.4
Nodes (3): item_name, target_qty, wo_to_complete

### Community 20 - "Community 20"
Cohesion: 0.5
Nodes (3): d, res, status_label

## Knowledge Gaps
- **132 isolated node(s):** `Seed master reference data for KEK IT Inventory`, `wo_to_complete`, `target_qty`, `item_name`, `bom_no` (+127 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `post_transaction()` connect `Community 7` to `Community 8`, `Community 0`, `Community 10`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `update_ledger()` connect `Community 8` to `Community 7`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `post_transaction()` (e.g. with `update_ledger()` and `test_payload_structure_camelcase_and_nested()`) actually correct?**
  _`post_transaction()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `complete_production_stage()` (e.g. with `.test_ideal_flow()` and `.test_role_based_permissions()`) actually correct?**
  _`complete_production_stage()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `get_production_stages()` (e.g. with `.test_ideal_flow()` and `.test_role_based_permissions()`) actually correct?**
  _`get_production_stages()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Seed master reference data for KEK IT Inventory`, `wo_to_complete`, `target_qty` to the rest of the system?**
  _132 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._