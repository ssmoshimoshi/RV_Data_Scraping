# 🏢 RUANG VISUAL — Market Intelligence & Lead Generation Pipeline

> **Sistem Otomatisasi Pencarian Calon Customer & Analisis Kompetitor Percetakan Wilayah Makassar**  
> Dibuat khusus untuk PT Estetika Ruang Visual berdasarkan dokumen acuan [`intelligence_pipeline_prd.md`](./intelligence_pipeline_prd.md).

---

## 📌 Modul yang Tersedia

| Modul | Status | Fungsi Utama |
| :--- | :---: | :--- |
| **Module B: Google Maps** | ✅ Siap Pakai | Ekstraksi calon customer (F&B, retail, EO) & percetakan kompetitor lengkap dengan **nomor WhatsApp/telepon** & alamat. |
| **Module E: Lead Scoring Engine** | ✅ Siap Pakai | Scoring otomatis 1–10 (🔥 HOT / 🟡 WARM / 🔵 COOL) & proyeksi kebutuhan cetak (kemasan, banner, stiker cup, dll). |
| **Module F: Competitor Matrix** | ✅ Siap Pakai | Pemetaan skala kapasitas kompetitor, analisis celah pelayanan/kualitas, dan strategi positioning RUANG VISUAL. |
| **Module C: Instagram Scraper** | ✅ Siap Pakai | Ekstraksi profil bisnis publik tanpa login (follower, bio, link bio WhatsApp, kategori). |
| **Module D: TikTok Market Signals** | ✅ Siap Pakai | Monitoring tren produk printing viral (packaging box, stiker die-cut) dan kebutuhan pasar terkini. |
| **Module A: Google Sheets Sync** | ⚙️ Siap Terhubung | Auto-sync data terstruktur ke 4 tab Google Sheets (Radar Prospek, Matriks Kompetitor, Market Signals, Scrape Log). |

---

## 🚀 Panduan Penggunaan Cepat

Aktifkan virtual environment terlebih dahulu:
```bash
source scrapers/.venv/bin/activate
```

### 1. Scrape Calon Customer (Leads) Baru di Makassar
```bash
# Uji coba 3 query (tanpa menulis ke Sheets)
python run_pipeline.py gmaps --mode leads --limit 3 --dry-run

# Jalankan live (ekspor ke Google Sheets)
python run_pipeline.py gmaps --mode leads --limit 5
```

### 2. Scrape Kompetitor Percetakan di Makassar
```bash
# Ekstraksi percetakan kompetitor beserta nomor telepon & rating
python run_pipeline.py gmaps --mode competitors --limit 3 --dry-run
```

### 3. Analisis Kelemahan Kompetitor & Matriks Strategi
```bash
# Analisis 16 kompetitor teratas dan rekomendasikan selling point RUANG VISUAL
python run_pipeline.py matrix --dry-run
```

### 4. Scrape Profil Publik Instagram
```bash
# Ekstraksi profil target / UMKM lokal Makassar
python run_pipeline.py instagram --profiles ruangvisual.id,kulinermakassar --dry-run
```

### 5. Pindai Tren & Sinyal Pasar TikTok
```bash
# Pindai tren produk printing viral & proyeksi demand
python run_pipeline.py tiktok --dry-run
```

---

## 📊 Lokasi Penyimpanan Data Lokal

Semua data hasil scraping secara otomatis tersimpan secara aman dalam format JSON:
- `data/raw/` : File mentah hasil ekstraksi dari platform.
- `data/processed/` : Data yang sudah di-scoring, diproses, dan siap dianalisis:
  - `leads_scored_*.json` : Calon customer dengan skor dan estimasi kebutuhan cetak.
  - `competitors_*.json` : Daftar kompetitor percetakan dengan kontak langsung.
  - `competitor_matrix_*.json` : Matriks analisis kompetisi dan strategi menang.
  - `market_signals_*.json` : Sinyal tren pasar dan produk viral.

---

## 🔗 Menghubungkan ke Google Sheets (Opsional)

Jika ingin data otomatis disinkronkan ke Google Sheets:
1. Letakkan file kredensial Google Service Account di `hermes-mcp-server/credentials/service-account.json`.
2. Buat file `hermes-mcp-server/.env`:
   ```env
   GOOGLE_SERVICE_ACCOUNT_FILE=credentials/service-account.json
   SPREADSHEET_ID=masukkan_id_spreadsheet_anda
   ```
3. Berikan akses edit (*Editor*) pada Google Sheet ke email Service Account Anda.
4. Jalankan inisialisasi tab:
   ```bash
   python run_pipeline.py init-sheets
   ```
