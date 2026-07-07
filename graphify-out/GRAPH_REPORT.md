# Graph Report - kek_it_inventory  (2026-07-07)

## Corpus Check
- 59 files · ~13,103 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 222 nodes · 223 edges · 37 communities (34 shown, 3 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 25 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `35adba59`
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
- [[_COMMUNITY_Community 31|Community 31]]

## God Nodes (most connected - your core abstractions)
1. `post_transaction()` - 14 edges
2. `process_sap_document_async()` - 8 edges
3. `TestSAPSync` - 8 edges
4. `create_kek_transaction()` - 7 edges
5. `Bounded Context: KEK IT Inventory Integration & Control (PPKEKI)` - 6 edges
6. `Domain Glossary` - 6 edges
7. `seed_master_data()` - 5 edges
8. `create_purchase_order()` - 5 edges
9. `update_ledger()` - 5 edges
10. `TestBridge` - 5 edges

## Surprising Connections (you probably didn't know these)
- `test_payload_structure_camelcase_and_nested()` --calls--> `post_transaction()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/api/test_poster.py → kek_it_inventory/kek_it_inventory/api/poster.py
- `seed_master_data()` --calls--> `setup_test_role_permissions()`  [INFERRED]
  kek_it_inventory/setup.py → kek_it_inventory/setup_role.py
- `run_simulation()` --calls--> `update_ledger()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/sim_workflow.py → kek_it_inventory/kek_it_inventory/api/ledger.py
- `run_delivery_simulation()` --calls--> `update_ledger()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/sim_delivery.py → kek_it_inventory/kek_it_inventory/api/ledger.py
- `post_transaction()` --calls--> `update_ledger()`  [INFERRED]
  kek_it_inventory/kek_it_inventory/api/poster.py → kek_it_inventory/kek_it_inventory/api/ledger.py

## Communities (37 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (18): Document, KEKAPICredential, KEKCompanyProfile, KEKComplianceArchive, KEKInventoryTransactionItem, KEKInventoryTransaction, KEKItemCustomsDoc, KEKItemMapping (+10 more)

### Community 1 - "Community 1"
Cohesion: 0.1
Nodes (23): create_kek_transaction(), Automatically creates a KEK Inventory Transaction from ERPNext documents 	with s, check_for_mismatch(), copy_parent_kek_details(), process_delivery_note(), process_purchase_order(), process_purchase_receipt(), process_subcontracting_order() (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (21): 1. Alur Inbound (Pemasukan), 1. Inbound Enforcement, 1. Indikator Status Visual (Status Banner), 2. Alur Outbound (Pengeluaran), 2. Emergency Bypass Policy, 2. Pesan Blokir yang Informatif & Solutif (Actionable Error Message), 3. Kendali Akses Kolom Bypass (Role-based Visibility), 3. Mismatch Status Triggers (+13 more)

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (12): create_purchase_order(), create_sales_order(), normalize_uom(), process_sap_document_async(), process_sap_xls_chunked(), XLS Chunked Background Processor (Hybrid Method). 	Driven by the 'SAP PO Import, Scheduled OData pull: fetches POs from SAP S/4HANA and creates them in ERPNext., Whitelisted POST endpoint for SAP HANA to push PO/SO data. (+4 more)

### Community 4 - "Community 4"
Cohesion: 0.15
Nodes (13): get_unique_key(), post_transaction(), process_queue(), Finds all QUEUED transactions and attempts to post them., Retrieves the dynamic X-Unique-Key from SINSW., Propagates status back to the source ERPNext document., Translates technical/JSON error messages from Bea Cukai/SINSW API  	into clear,, Posts a KEK Inventory Transaction to SINSW Gateway following KEK PDF standards. (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (6): download_customs_xls(), manual_validate_ppkek(), Memvalidasi status PPKEK secara manual oleh KEK Manager.     Mengubah status dok, Generate XLS file containing item details structured for Bea Cukai KEK/CEISA upl, test_manual_validate_ppkek(), TestBridge

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (12): 1. Hakekat PPKEK: Unifikasi Dokumen Kepabeanan KEK, 2.1 Outbound: PPKEK Pengeluaran Sementara (ex-BC 2.6.1) - Kode `0407633`, 2.2 Inbound: PPKEK Pemasukan Kembali (ex-BC 2.6.2) - Kode `0407614`, 2. Alur Integrasi Spesifik Kasus Subkontrak (Maklon), 3.1 Penambahan Barang Lokal (TLDDP) di Lokasi Subkontraktor, 3.2 Manajemen Selisih BOM (BOM Discrepancy & Limit Toleransi), 3. Resolusi Masalah Operasional Tingkat Lanjut, code:sql (-- Contoh Pemisahan Asal Barang pada KEK Stock Ledger) (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (5): Fungsi ini berjalan otomatis sebelum setiap test dijalankan. 		FrappeTestCase ak, test_payload_structure_camelcase_and_nested(), TestPosterAPI, FrappeTestCase, TestKEKRefActivityCode

### Community 8 - "Community 8"
Cohesion: 0.38
Nodes (5): create_kek_custom_fields(), Seed master reference data for KEK IT Inventory, setup_test_role_permissions(), seed_doctype(), seed_master_data()

### Community 9 - "Community 9"
Cohesion: 0.29
Nodes (4): Records movements into KEK Stock Ledger from a SENT transaction., update_ledger(), run_delivery_simulation(), run_simulation()

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (6): code:bash (cd $PATH_TO_YOUR_BENCH), code:bash (cd apps/kek_it_inventory), Contributing, Installation, KEK IT Inventory, License

### Community 11 - "Community 11"
Cohesion: 0.33
Nodes (3): Immediately enqueue the chunked XLS processor after the job record is created., Reset progress fields if file changes and status is being re-queued, SAPPOImportJob

### Community 12 - "Community 12"
Cohesion: 0.4
Nodes (4): daily_payload_summary(), get_failed_count(), Mengirim ringkasan transaksi kemarin ke tim operasional., Mengembalikan jumlah transaksi yang gagal untuk ditampilkan di badge desktop.

### Community 13 - "Community 13"
Cohesion: 0.7
Nodes (4): execute(), get_chart_data(), get_columns(), get_data()

## Knowledge Gaps
- **55 isolated node(s):** `Seed master reference data for KEK IT Inventory`, `Mengembalikan jumlah transaksi yang gagal untuk ditampilkan di badge desktop.`, `Mengirim ringkasan transaksi kemarin ke tim operasional.`, `Daily sync between Local and SINSW`, `Reset progress fields if file changes and status is being re-queued` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `post_transaction()` connect `Community 4` to `Community 9`, `Community 1`, `Community 7`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `test_payload_structure_camelcase_and_nested()` connect `Community 7` to `Community 4`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `update_ledger()` connect `Community 9` to `Community 4`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `post_transaction()` (e.g. with `test_payload_structure_camelcase_and_nested()` and `update_ledger()`) actually correct?**
  _`post_transaction()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `process_sap_document_async()` (e.g. with `.test_process_sap_document_async_success()` and `.test_idempotency()`) actually correct?**
  _`process_sap_document_async()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `create_kek_transaction()` (e.g. with `process_purchase_receipt()` and `process_delivery_note()`) actually correct?**
  _`create_kek_transaction()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Seed master reference data for KEK IT Inventory`, `Mengembalikan jumlah transaksi yang gagal untuk ditampilkan di badge desktop.`, `Mengirim ringkasan transaksi kemarin ke tim operasional.` to the rest of the system?**
  _55 weakly-connected nodes found - possible documentation gaps or missing edges._