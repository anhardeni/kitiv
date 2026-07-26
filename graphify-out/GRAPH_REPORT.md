# Graph Report - kek_it_inventory  (2026-07-26)

## Corpus Check
- 109 files · ~35,158 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 450 nodes · 583 edges · 68 communities (45 shown, 23 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `310c5f59`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SAPPOImportJob
- kek_service.py
- TestSAPSync
- complete_production_stage
- TestBridge
- post_transaction
- Bounded Context: KEK IT Inventory Integration & Control (PPKEKI)
- work_order.js
- update_ledger
- mapping_engine.py
- Panduan Integrasi PPKEK: Pemberitahuan Pabean Kawasan Ekonomi Khusus
- sap_sync.py
- TestPosterAPI
- ensure_item
- seed_master_data
- README.md
- kek_it_inventory/utils.py
- KEKAPICredential
- execute
- run_automated_mapping_check
- Document
- kek_inventory_transaction.js
- create_kek_workspace.py
- daily_reconciliation
- dialog
- TestKEKAPICredential
- parse_sap_odata_date
- KEKItemTolerance
- KEKCompanyProfile
- KEKComplianceArchive
- KEKInventoryTransactionItem
- KEKInventoryTransaction
- KEKItemCustomsDoc
- KEKItemMapping
- KEKRefActivityCode
- KEKRefCustomsDocument
- KEKRefItemCategory
- KEKRefTransactionType
- KEKRefUnit
- KEKStockLedger
- KEKStockSnapshot
- SAPIntegrationConfig
- SAPIntegrationLog
- kek_it_inventory

## God Nodes (most connected - your core abstractions)
1. `post_transaction()` - 26 edges
2. `TestSAPSync` - 25 edges
3. `TestBridge` - 18 edges
4. `complete_production_stage()` - 13 edges
5. `process_sap_xls_chunked()` - 11 edges
6. `execute_live_sap_sync_from_push()` - 11 edges
7. `get_production_stages()` - 11 edges
8. `create_kek_transaction()` - 10 edges
9. `update_ledger()` - 10 edges
10. `TestManufactureService` - 10 edges

## Surprising Connections (you probably didn't know these)
- `test_payload_structure_camelcase_and_nested()` --calls--> `post_transaction()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/api/test_poster.py → kek_it_inventory/kek_it_inventory/api/poster.py
- `test_post_stock_reconciliation_payload()` --calls--> `post_transaction()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/tests/test_poster.py → kek_it_inventory/kek_it_inventory/api/poster.py
- `test_post_transaction_with_real_creds()` --calls--> `post_transaction()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/tests/test_poster.py → kek_it_inventory/kek_it_inventory/api/poster.py
- `test_update_customs_documents()` --calls--> `update_customs_documents()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/tests/test_poster.py → kek_it_inventory/kek_it_inventory/api/poster.py
- `test_process_queue()` --calls--> `process_queue()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/tests/test_poster.py → kek_it_inventory/kek_it_inventory/api/poster.py

## Import Cycles
- None detected.

## Communities (68 total, 23 thin omitted)

### Community 0 - "SAPPOImportJob"
Cohesion: 0.29
Nodes (4): Document, Immediately enqueue the chunked XLS processor after the job record is created., Reset progress fields if file changes and status is being re-queued, SAPPOImportJob

### Community 1 - "kek_service.py"
Cohesion: 0.05
Nodes (47): create_kek_transaction(), Automatically creates a KEK Inventory Transaction from ERPNext documents 	with s, get_unique_key(), get_update_endpoint(), post_transaction(), process_queue(), Constructs the correct PUT update URL: 	- Real: {base_url}/transaksi/dokumen 	-, Retrieves the dynamic X-Unique-Key from SINSW. (+39 more)

### Community 2 - "TestSAPSync"
Cohesion: 0.17
Nodes (3): process_sap_document_async(), Asynchronously processes an SAP Integration Log record., TestSAPSync

### Community 3 - "complete_production_stage"
Cohesion: 0.11
Nodes (22): adjust_subsequent_wos(), check_manufacture_permission(), complete_production_stage(), create_sub_work_orders(), ensure_custom_fields(), get_bom_hierarchy(), get_item_default_warehouse(), get_production_stages() (+14 more)

### Community 4 - "TestBridge"
Cohesion: 0.06
Nodes (11): check_for_mismatch(), download_customs_xls(), manual_validate_ppkek(), Membandingkan item & qty di KEK Inventory Transaction dengan source ERPNext docu, Job periodik untuk mengecek seluruh transaksi KEK 30 hari terakhir., Memvalidasi status PPKEK secara manual oleh KEK Manager.     Mengubah status dok, Generate XLS file containing item details structured for Bea Cukai KEK/CEISA upl, run_mismatch_check_job() (+3 more)

### Community 5 - "post_transaction"
Cohesion: 0.33
Nodes (6): copy_parent_kek_details(), Menyalin nomor_ppkek dan kek_status dari PO/SO asal ke Receipt., Memvalidasi status PPKEK sebelum receipt disubmit.     Harus berstatus 'ACKNOWLE, Menyalin nomor_ppkek dan tanggal_ppkek langsung dari parent document (PO/SO) ke, Memvalidasi status PPKEK sebelum receipt/Delivery Note disubmit.     Harus berst, validate_kek_submission()

### Community 6 - "Bounded Context: KEK IT Inventory Integration & Control (PPKEKI)"
Cohesion: 0.10
Nodes (20): 1. Alur Inbound (Pemasukan), 1. Inbound Enforcement, 1. Indikator Status Visual (Status Banner), 2. Alur Outbound (Pengeluaran), 2. Emergency Bypass Policy, 2. Pesan Blokir yang Informatif & Solutif (Actionable Error Message), 3. Kendali Akses Kolom Bypass (Role-based Visibility), 3. Mismatch Status Triggers (+12 more)

### Community 7 - "work_order.js"
Cohesion: 0.12
Nodes (13): bom_no, item_name, qty_actual_formatted, qty_target_formatted, stage_name, $step_node, $stepper, $table_body (+5 more)

### Community 8 - "update_ledger"
Cohesion: 0.17
Nodes (14): Records movements into KEK Stock Ledger from a SENT transaction., update_ledger(), get_unique_key(), post_transaction(), process_queue(), Finds all QUEUED transactions and attempts to post them., Retrieves the dynamic X-Unique-Key from SINSW., Propagates status back to the source ERPNext document. (+6 more)

### Community 9 - "mapping_engine.py"
Cohesion: 0.17
Nodes (17): execute_hourly_sync(), execute_live_sap_sync(), execute_live_sap_sync_from_push(), _fail_log(), _get_default_warehouse(), Engine Universal Sinkronisasi Live dengan pengaman alur transaksi SO/PO, Safely retrieves a default warehouse for the given item and company., Menulis rekaman histori sinkronisasi terisolasi (+9 more)

### Community 10 - "Panduan Integrasi PPKEK: Pemberitahuan Pabean Kawasan Ekonomi Khusus"
Cohesion: 0.12
Nodes (15): 1.1 Penyesuaian Fisik & Selisih Pabean (Stock Opname & Adjustment), 1. Hakekat PPKEK: Unifikasi Dokumen Kepabeanan KEK, 2.1 Outbound: PPKEK Pengeluaran Sementara (ex-BC 2.6.1) - Kode `0407633`, 2.2 Inbound: PPKEK Pemasukan Kembali (ex-BC 2.6.2) - Kode `0407614`, 2. Alur Integrasi Spesifik Kasus Subkontrak (Maklon), 3.1 Penambahan Barang Lokal (TLDDP) di Lokasi Subkontraktor, 3.2 Manajemen Selisih BOM (BOM Discrepancy & Limit Toleransi), 3. Resolusi Masalah Operasional Tingkat Lanjut (+7 more)

### Community 11 - "sap_sync.py"
Cohesion: 0.11
Nodes (19): create_purchase_order(), create_sales_order(), normalize_sap_me2n_columns(), normalize_uom(), parse_date_string(), parse_float(), process_sap_xls_chunked(), Whitelisted POST endpoint for SAP to push PO/SO data.     Identifies the correct (+11 more)

### Community 12 - "TestPosterAPI"
Cohesion: 0.15
Nodes (9): FrappeTestCase, FrappeTestCase, Fungsi ini berjalan otomatis sebelum setiap test dijalankan. 		FrappeTestCase ak, Menguji apakah payload JSON yang dibentuk sesuai dengan standar KEK.PDF, TestPosterAPI, FrappeTestCase, TestKEKRefActivityCode, FrappeTestCase (+1 more)

### Community 13 - "ensure_item"
Cohesion: 0.27
Nodes (7): ensure_item(), ensure_supplier_or_customer(), get_default_warehouse(), Lazy Master Data Creation for Supplier or Customer.     If entity_name doesn't e, Lazy Master Data Creation for Item.     If item_code doesn't exist in ERPNext, c, Retrieves default non-group warehouse for PO/SO stock items matching company., Tests that importing a PO with an already existing custom_sap_po_number does NOT

### Community 14 - "seed_master_data"
Cohesion: 0.42
Nodes (7): create_kek_custom_fields(), Seed master reference data for KEK IT Inventory, setup_kek_manager_permissions(), setup_kek_user_permissions(), setup_test_role_permissions(), seed_doctype(), seed_master_data()

### Community 15 - "README.md"
Cohesion: 0.29
Nodes (6): code:bash (cd $PATH_TO_YOUR_BENCH), code:bash (cd apps/kek_it_inventory), Contributing, Installation, KEK IT Inventory, License

### Community 16 - "kek_it_inventory/utils.py"
Cohesion: 0.40
Nodes (4): daily_payload_summary(), get_failed_count(), Mengirim ringkasan transaksi kemarin ke tim operasional., Mengembalikan jumlah transaksi yang gagal untuk ditampilkan di badge desktop.

### Community 18 - "execute"
Cohesion: 0.70
Nodes (4): execute(), get_chart_data(), get_columns(), get_data()

### Community 19 - "run_automated_mapping_check"
Cohesion: 0.29
Nodes (4): auto_repair_sap_mappings(), Sandbox untuk pengujian kegagalan parsing skema JSON mentah, Membaca payload sampel untuk melakukan perbaikan otomatis pada tabel anak, run_automated_mapping_check()

### Community 20 - "Document"
Cohesion: 0.33
Nodes (4): Document, Document, SAPFieldMappingLine, SAPSyncSettings

### Community 21 - "kek_inventory_transaction.js"
Cohesion: 0.50
Nodes (3): d, res, status_label

## Knowledge Gaps
- **42 isolated node(s):** `kek_it_inventory`, `wo_to_complete`, `target_qty`, `item_name`, `bom_no` (+37 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `post_transaction()` connect `kek_service.py` to `update_ledger`, `TestPosterAPI`, `TestBridge`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Why does `get_unique_key()` connect `kek_service.py` to `KEKAPICredential`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `KEKAPICredential` connect `KEKAPICredential` to `kek_service.py`, `Document`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `post_transaction()` (e.g. with `test_payload_structure_camelcase_and_nested()` and `process_purchase_order()`) actually correct?**
  _`post_transaction()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `kek_it_inventory`, `wo_to_complete`, `target_qty` to the rest of the system?**
  _42 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `kek_service.py` be split into smaller, more focused modules?**
  _Cohesion score 0.051203277009728626 - nodes in this community are weakly interconnected._
- **Should `complete_production_stage` be split into smaller, more focused modules?**
  _Cohesion score 0.11229946524064172 - nodes in this community are weakly interconnected._