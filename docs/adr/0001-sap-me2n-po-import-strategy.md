# 1. Strategy Impor Purchasing Order Ekspor SAP ME2N

* **Status:** Accepted
* **Tanggal:** 2026-07-24

## Konteks & Masalah
Pengguna perlu mengimpor file ekspor transaksi SAP ME2N (format `.xlsx` seperti `Copy of Trial PO-IT Inventory.xlsx`) ke dalam ERPNext untuk menghasilkan dokumen `Purchase Order`. File tersebut memiliki 55 kolom dengan header bawaan SAP (seperti `Purchasing Document`, `Material`, `Order Quantity`, `Net Price`, `Supplier/Supplying Plant`, dll.).

Sistem perlu memproses file ini secara efisien tanpa memerlukan pengubahan manual kolom file Excel oleh user, serta menangani master data (Item & Supplier) yang mungkin belum ada di ERPNext.

## Keputusan
1. **Direct Ingestion & Smart Column Mapping**:
   Menggunakan `SAP PO Import Job` (`process_sap_xls_chunked`) dengan layer pemetaan kolom fleksibel yang mengenali header standar SAP ME2N secara otomatis dan mengelompokkan baris berdasarkan `Purchasing Document` untuk menghasilkan dokumen ERPNext `Purchase Order`.
2. **Lazy Master Data Creation**:
   Jika `Supplier` atau `Item` belum terdaftar di database ERPNext saat proses impor berjalan, sistem akan secara otomatis membuat dokumen master `Supplier` dan `Item` baru (dengan UOM dan Deskripsi dari Excel) sebelum membuat dokumen `Purchase Order`.
3. **Penyimpanan Nomor PO SAP pada `custom_sap_po_number`**:
   Nomor PO SAP (`Purchasing Document`, misal `4600177687`) disimpan di field kustom `custom_sap_po_number` pada dokumen `Purchase Order` untuk pelacakan, audit log, dan pencegahan impor duplikat. Naming ID dokumen ERPNext tetap menggunakan konvensi standar (`PUR-ORD-.YYYY.-.#####.`).
4. **Initial Status Draft**:
   Dokumen `Purchase Order` yang dihasilkan disimpan dalam status `Draft` untuk memberikan kesempatan bagi Staf Pembelian/Gudang memverifikasi data sebelum di-submit dan memicu alur pabean PPKEK.

## Konsekuensi
* **Positif**:
  * User tidak perlu mengedit atau membersihkan header file ekspor SAP sebelum mengunggah.
  * Impor berkas berukuran besar tidak terhenti akibat ketidaktersediaan item/supplier baru.
  * Mencegah pemuatan duplikat dokumen SAP PO yang sama secara otomatis.
* **Risiko / Mitigasi**:
  * Master data Item/Supplier yang dibuat otomatis menggunakan atribut default; staf perlu memperbarui rincian tambahan (seperti Item Group atau Supplier Group khusus) jika diperlukan setelah impor.
