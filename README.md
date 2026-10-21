# RUANG VISUAL - Market Intelligence & Lead Generation Pipeline

> **Sistem Otomatisasi Pencarian Calon Customer & Analisis Kompetitor Percetakan Wilayah Makassar**  
> Dibuat khusus untuk PT Estetika Ruang Visual berdasarkan dokumen acuan [`intelligence_pipeline_prd.md`](./intelligence_pipeline_prd.md).

---

## Modul yang Tersedia

Setiap platform mengumpulkan **3 jenis data**: Calon Customer (Leads), Kompetitor, dan Tren Pasar (Market Signals).

| Platform | Status | Data yang Dikumpulkan |
| :--- | :---: | :--- |
| **Google Maps** | Siap Pakai | **Leads**: F&B, retail, EO, klinik dengan nomor WhatsApp<br>**Competitors**: Percetakan lokal dengan rating & kontak<br>**Trends**: Supplier packaging & bahan printing |
| **Instagram** | Siap Pakai | **Leads**: Bisnis lokal UMKM dengan profil publik<br>**Competitors**: Akun percetakan Makassar<br>**Trends**: Hashtag & estetika branding populer |
| **TikTok** | Siap Pakai | **Leads**: Kreator UMKM & usaha baru Makassar<br>**Competitors**: Vendor cetak aktif promosi<br>**Trends**: Produk printing viral (stiker hologram, box custom) |
| **Facebook Marketplace** | Siap Pakai | **Leads**: Penjual kuliner & produk fisik<br>**Competitors**: Jasa percetakan di Marketplace<br>**Trends**: Produk terlaris & rentang harga |
| **Threads** | Siap Pakai | **Leads**: Post bisnis lokal promosi<br>**Competitors**: Vendor percetakan aktif di Threads<br>**Trends**: Tren branding & packaging viral |
| **Lead Scoring Engine** | Siap Pakai | Scoring otomatis 1–10 (HOT / WARM / COOL) & proyeksi kebutuhan cetak |
| **Competitor Matrix** | Siap Pakai | Analisis celah kompetitor & strategi positioning RUANG VISUAL |
| **Google Sheets Sync** | Siap Terhubung | Auto-sync ke 3 tab: Radar Prospek, Matriks Kompetitor, Market Signals |

---

## Panduan Penggunaan Cepat

Aktifkan virtual environment terlebih dahulu:
```bash
source scrapers/.venv/bin/activate
```

### 1. Scrape dari Semua Platform (Mode Lengkap)

Setiap platform dapat scrape **leads**, **competitors**, dan **trends** secara bersamaan:

```bash
# Google Maps: leads + competitors + trends
python run_pipeline.py gmaps --mode all --limit 3 --dry-run

# Instagram: leads + competitors + trends
python run_pipeline.py instagram --mode all --dry-run

# TikTok: leads + competitors + trends
python run_pipeline.py tiktok --mode all --dry-run

# Facebook Marketplace: leads + competitors + trends
python run_pipeline.py facebook --mode all --dry-run

# Threads: leads + competitors + trends
python run_pipeline.py threads --mode all --dry-run
```

### 2. Scrape Per Kategori Data

Atau scrape hanya kategori tertentu:

```bash
# Hanya Leads (Calon Customer)
python run_pipeline.py gmaps --mode leads --limit 5
python run_pipeline.py instagram --mode leads --dry-run
python run_pipeline.py threads --mode leads --dry-run

# Hanya Competitors
python run_pipeline.py gmaps --mode competitors --limit 3
python run_pipeline.py tiktok --mode competitors --dry-run

# Hanya Trends (Market Signals)
python run_pipeline.py gmaps --mode trends --limit 3
python run_pipeline.py facebook --mode trends --dry-run
```

### 3. Analisis Kelemahan Kompetitor & Matriks Strategi
```bash
# Analisis kompetitor teratas dan rekomendasikan selling point RUANG VISUAL
python run_pipeline.py matrix --dry-run
```

---

## Lokasi Penyimpanan Data Lokal

Semua data hasil scraping secara otomatis tersimpan secara aman dalam format JSON:
- `data/raw/` : File mentah hasil ekstraksi dari platform.
- `data/processed/` : Data yang sudah di-scoring, diproses, dan siap dianalisis:
  - `leads_scored_*.json` : Calon customer dengan skor dan estimasi kebutuhan cetak.
  - `competitors_*.json` : Daftar kompetitor percetakan dengan kontak langsung.
  - `competitor_matrix_*.json` : Matriks analisis kompetisi dan strategi menang.
  - `market_signals_*.json` : Sinyal tren pasar dan produk viral.

---

## Menghubungkan ke Google Sheets (Opsional)

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
