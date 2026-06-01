# Panduan Integrasi PPKEK: Pemberitahuan Pabean Kawasan Ekonomi Khusus
## Kepatuhan Bea Cukai PER-24/BC/2021 Berbasis KEK IT Inventory & ERPNext

> [!NOTE]
> **Advisory Note:** Dokumen ini berfungsi sebagai spesifikasi fungsional dan panduan kepatuhan untuk integrasi dokumen **PPKEK (Pemberitahuan Pabean Kawasan Ekonomi Khusus)** pada custom app `kek_it_inventory`. PPKEK adalah dokumen tunggal yang menyatukan seluruh aktivitas pabean masuk-keluar di kawasan KEK sesuai regulasi PMK-237/PMK.04/2020.

---

## 1. Hakekat PPKEK: Unifikasi Dokumen Kepabeanan KEK

Di Kawasan Ekonomi Khusus (KEK), dokumen kepabeanan tradisional (seperti BC 2.3, BC 4.0, BC 3.0, BC 2.7, BC 2.6.1, BC 2.6.2) tidak lagi digunakan secara mandiri. Seluruh dokumen tersebut disatukan ke dalam satu format dokumen pabean konsolidasi yang disebut **PPKEK (PJ.01)**.

Sistem KEK IT Inventory bertindak sebagai penerjemah transaksi ERPNext ke dalam kode-kode aktivitas PPKEK yang diakui oleh portal **SINSW/CEISA 4.0**:

### 📊 Pemetaan Aktivitas Tradisional ke PPKEK

| Dokumen Tradisional | Jenis Aktivitas PPKEK | Kode Bea Cukai (kd_kegiatan) | Trigger Dokumen ERPNext |
| :--- | :--- | :--- | :--- |
| **BC 2.3** (Impor) | PPKEK Pemasukan ex-LDP | `0407611` | Purchase Receipt (Luar Negeri) |
| **BC 4.0** (Lokal) | PPKEK Pemasukan ex-TLDDP | `0407613` | Purchase Receipt (Dalam Negeri) |
| **BC 2.7** (Mutasi TPB) | PPKEK Pemasukan ex-Kawasan Berikat/TPB | `0407621` / `0407521` | Stock Entry (Material Receipt) |
| **BC 2.6.1** (Subkon Keluar) | PPKEK Pengeluaran Sementara (Subkon) | **`0407633`** | Stock Entry (Send to Subcontractor) |
| **BC 2.6.2** (Subkon Masuk) | PPKEK Pemasukan Kembali ex-Subkon | **`0407614`** | Subcontracting Receipt |
| **BC 3.0** (Ekspor) | PPKEK Pengeluaran ke LDP (Ekspor) | `0407631` | Delivery Note (Luar Negeri) |
| **BC 2.5** (Lokal Keluar) | PPKEK Pengeluaran ke TLDDP (Domestik) | `0407632` | Delivery Note (Dalam Negeri) |

---

## 2. Alur Integrasi Spesifik Kasus Subkontrak (Maklon)

Pekerjaan subkontrak di KEK menggunakan dua dokumen PPKEK yang saling berpasangan untuk melacak pergerakan bahan baku:

### 2.1 Outbound: PPKEK Pengeluaran Sementara (ex-BC 2.6.1) - Kode `0407633`
*   **Trigger**: Dokumen `Stock Entry` dengan tipe `Send to Subcontractor` di ERPNext.
*   **Logika Sistem**:
    1.  Sistem menyaring daftar bahan baku yang dikirim ke subcontractor.
    2.  Menerjemahkan kode item internal ERPNext menjadi `Customs Item Code` via `KEK Item Mapping`.
    3.  Mengirimkan payload JSON PPKEK Pengeluaran Sementara ke SINSW.
    4.  Setelah mendapat ACK, sistem mengunci stok di gudang virtual subkon sebagai persediaan yang sedang dikerjakan di luar kawasan pabean.

### 2.2 Inbound: PPKEK Pemasukan Kembali (ex-BC 2.6.2) - Kode `0407614`
*   **Trigger**: Dokumen `Subcontracting Receipt` ketika barang setengah jadi atau barang jadi masuk kembali ke KEK.
*   **Logika Sistem**:
    1.  Membaca referensi nomor pengiriman PPKEK ex-BC 2.6.1 sebelumnya untuk verifikasi pelacakan saldo.
    2.  Menghitung proporsi bahan baku yang dikonsumsi menggunakan standar BOM.
    3.  Memasukkan nilai realisasi dan membuat dokumen PPKEK Pemasukan Kembali.

---

## 3. Resolusi Masalah Operasional Tingkat Lanjut

### 3.1 Penambahan Barang Lokal (TLDDP) di Lokasi Subkontraktor
Jika saat pengerjaan di subcontractor ditambahkan barang lokal yang tidak terdaftar pada dokumen pengiriman awal (BC 2.6.1):

*   **Aturan Kepatuhan**: Kelebihan berat/nilai barang lokal wajib dilaporkan secara eksplisit pada dokumen **PPKEK Pemasukan Kembali (BC 2.6.2)** sebagai **"Bahan Baku Tambahan Asal TLDDP"**.
*   **Prinsip Perpajakan**: Deklarasi ini wajib didukung oleh Faktur Pajak dari subkon (dengan kode 07 - PPN tidak dipungut di KEK) dan Invoice Pembelian Lokal.
*   **Dampak Ledger**: Sistem KEK IT Inventory melakukan *Origin Split* pada `tabKEK Stock Ledger` untuk mencatat porsi barang lokal tersebut terbebas dari Bea Masuk jika produk jadi nantinya dijual ke pasar domestik Indonesia.

```sql
-- Contoh Pemisahan Asal Barang pada KEK Stock Ledger
INSERT INTO `tabKEK Stock Ledger` 
(name, customs_item_code, qty_in, origin_type, voucher_no, description)
VALUES 
('SL-0001', 'COMP-01', 80.0000, 'IMPORT', 'BC-262-XXXX', 'Porsi Bahan Baku ex-Impor ex-BC 2.6.1'),
('SL-0002', 'COMP-01', 20.0000, 'TLDDP', 'BC-262-XXXX', 'Porsi Tambahan Lokal dari Subkontraktor');
```

### 3.2 Manajemen Selisih BOM (BOM Discrepancy & Limit Toleransi)
Untuk meminimalisir kegagalan pelaporan akibat deviasi konsumsi bahan baku di lapangan, sistem menerapkan **Opsi II: Flexible Tolerance Limit** menggunakan DocType **`KEK Item Tolerance`**:

```
                  [ Subcontracting Receipt Di-submit ]
                                    │
                                    ▼
                [ Hitung Deviasi Konsumsi vs. Standar BOM ]
                                    │
                                    ▼
               { Apakah Deviasi <= KEK Item Tolerance? }
                 /                                   \
               YA                                  TIDAK
               /                                       \
  [ Auto-Settle via Yield Loss ]            [ Tandai Flag & Alert System ]
   - Laporkan dengan kode asli               - Tahan antrean pabean
   - Kirim otomatis ke Bea Cukai             - Selesaikan via dokumen
                                               Adjustment (kd 33) atau
                                               Scrap Return (Kategori 8)
```

1.  **Validasi Otomatis**: Jika varians masih berada dalam batas persentase toleransi `tolerance_percentage` (misalnya ≤ 3%), transaksi langsung dilaporkan ke Bea Cukai menggunakan kode barang asli tanpa memblokir operasional gudang.
2.  **Pemberitahuan Khusus**: Jika varians melebihi batas toleransi, sistem menahan pengiriman dokumen PPKEK dan mengirimkan alert kepada staf pabean untuk menyelesaikannya secara legal melalui dokumen penyesuaian pabean (**Adjustment `kd_kegiatan 33`**) atau pengembalian sisa bahan fisik sebagai **Scrap (`kd_kategori_barang: 8`)**.

---
*PwC Consulting Indonesia - Kepatuhan & Arsitektur Logistik Pabean KEK*
