# RUANG VISUAL — Market Intelligence & Autonomous B2B Prospecting Engine

Sistem intelijen pasar dan akuisisi pelanggan B2B percetakan komersial terpadu berbasis multi-platform.
Repositori ini telah dirombak total dari sistem lama (*legacy blind scraping*) menjadi sistem terarah berbasis validasi aktivitas akun riil dan penyimpanan relasional Supabase.

---

## 1. Dokumen Acuan Arsitektur & Spesifikasi

- **Spesifikasi Persyaratan Produk (PRD v2.0 Enterprise)**:
  [PRD_RUANG_VISUAL_MARKET_INTELLIGENCE.md](./PRD_RUANG_VISUAL_MARKET_INTELLIGENCE.md)
  Menjelaskan arsitektur lengkap 10 bab: Visi & Unit Economics, Taksonomi Produk Cetak, Vektor Ekstraksi Multi-Platform, Algoritma Scoring Matematis, Skema Lengkap DDL PostgreSQL/Supabase, Desain UI CMYK Next.js, SOP Pengiriman Sampel Fisik, dan Protokol Kolaborasi Multi-Agen.

- **Diagram Alur Rinci Multi-Platform (Resolusi Tinggi)**:
  [docs/flowcharts/flowchart_multiplatform_scraping_detailed.png](./docs/flowcharts/flowchart_multiplatform_scraping_detailed.png)

- **Dokumen Spesifikasi Titik Data Ekstraksi**:
  [docs/flowcharts/DETAIL_EKSTRAKSI_MULTIPLATFORM.md](./docs/flowcharts/DETAIL_EKSTRAKSI_MULTIPLATFORM.md)

---

## 2. Struktur Repositori Terkini

```
DATA CALON CUSTOMER/
|-- .agents/                          # Aturan kolaborasi agen dan skill internal
|-- .env                              # Kredensial lingkungan (Supabase, Apify API Token)
|-- AGENTS.md                         # Pedoman pembagian peran Kilo dan Antigravity
|-- PRD_RUANG_VISUAL_MARKET_INTELLIGENCE.md # Dokumen PRD utama v2.0
|-- README.md                         # Ringkasan proyek dan panduan repositori
|-- data/                             # Penyimpanan lokal sementara (raw / processed)
|   |-- raw/
|   `-- processed/
|-- docs/
|   `-- flowcharts/                   # Aset visual diagram alur arsitektur dan spesifikasi data
|       |-- DETAIL_EKSTRAKSI_MULTIPLATFORM.md
|       |-- flowchart_high_level_pipeline.png
|       `-- flowchart_multiplatform_scraping_detailed.png
|-- requirements.txt                  # Dependensi Python untuk mesin ekstraksi
`-- scrapers/                         # Modul ekstraksi data modular (Crawlee Python & API)
```

---

## 3. Pilar Arsitektur Sistem

1. **Mesin Ekstraksi Hibrida**:
   - Engine Lokal Gratis (Crawlee Python & TLS Client) untuk Google Maps, Threads, dan Marketplace.
   - Apify Cloud Actors untuk operasi massal yang memerlukan ribuan rotasi IP proxy (Followers Instagram, Meta Ads Library).
2. **Penyaring Anti-Blind Scraping (Verification Guard)**:
   - Wajib postingan aktif kurang dari 30 hari.
   - Normalisasi nomor WhatsApp format internasional baku `628xxxxxxxxxx`.
   - Algoritma Lead Scoring deterministik (1 - 100).
3. **Penyimpanan Relasional Supabase**:
   - Menggantikan flat spreadsheet dengan 5 tabel relasional: `target_sources`, `leads`, `lead_insights`, `crm_outreach`, `competitor_matrix`.
4. **Dashboard Lokal Berstandar UI CMYK RUANG VISUAL**:
   - Dibangun dengan Next.js App Router mengadopsi palet CMYK (`cmyk-cyan`, `cmyk-key`, `bg-surface`, `neutral-paper`).
   - Fitur Kanban CRM, aksi 1-klik WhatsApp terpersonalisasi, dan pelacakan pengiriman paket sampel fisik (*sample box*).
