# STANDAR OPERASIONAL DAN SPESIFIKASI PENEMPATAN DATA SCRAPING RUANG VISUAL
## Dokumen Patokan Arsitektur Data, Skema Multi-Layanan, dan Distribusi Output
### Adendum Resmi PRD v2.0: Perluasan 5 Pilar Layanan & Pemanfaatan Open-Source

---

## 1. Status Dokumen dan Relevansi PRD v2.0

Dokumen ini merupakan **adendum teknis resmi** yang melengkapi dan memperluas dokumen utama `PRD_RUANG_VISUAL_MARKET_INTELLIGENCE.md`.

**Ruang Lingkup Perluasan**:
Dokumen adendum ini memperluas cakupan deteksi pasar dari fokus awal kemasan kuliner menjadi kapasitas produksi terpadu RUANG VISUAL (16 template produk dan 100 master items) yang mencakup 5 pilar layanan utama. Selain itu, dokumen ini menetapkan pemanfaatan pustaka open-source lokal dan isolasi data prospek ke SQLite lokal guna menjamin efisiensi biaya dan perlindungan penuh atas basis data produksi Supabase.

---

## 2. Pemetaan 5 Pilar Layanan Master RUANG VISUAL

| Pilar Layanan | Produk Master Terkait | Sektor Sasaran Utama di Makassar | Pemicu Kebutuhan (*Trigger Signal*) |
|---|---|---|---|
| **1. Reklame & Promosi Visual** | Spanduk Flexy Korea & Cina, Roll-Up Banner, Cetak Albatros B2B, Luster, Silk, Cutting Sticker Oracal, Stiker Reflektif | Usaha baru buka (*Grand Opening*), klinik kecantikan, ruko/toko retail, dealer properti, event pameran | Status listing tempat baru di Maps, ulasan lokasi sulit dicari, postingan promo musiman |
| **2. Merchandise & Souvenir Custom** | Ganci Akrilik UV 3mm Laser Cut, Sablon Mug + Box, PIN Peniti (44/58), PIN Ganci 2 Sisi, Tote Bag Kanvas, Tas Spunbond 2 Sisi | Komunitas hobi/otomotif, kafe yang menjual merchandise, event organizer, panitia festival | Tagar komunitas, pengumuman acara/gathering, penjualan tiket/merchandise resmi di bio/feed |
| **3. Konveksi & Sablon Tekstil** | Sablon Kaos DTF (Cotton Combed 24s/30s Lengan Pendek & Panjang), DTF Printing Roll-to-Roll | Restoran/kafe (seragam staf), panitia acara kampus, instansi, clothing line lokal Makassar | Ulasan foto staf belum berseragam rapi, pengumuman rekrutmen karyawan baru, dies natalis |
| **4. Institusi, Sekolah & Kantor** | Map Raport + Siku Plastik, ID Card Instant & UV Flatbed PVC, Tali Lanyard Tissue, Stempel Flash, Jilid Lem Panas, Cetak Offset A3+ | Sekolah (SD/SMP/SMA/SMK), madrasah, pesantren, bimbel, kantor notaris, kantor hukum, klinik | Kalender tahun ajaran baru (PPDB), direktori sekolah formal, listing kantor hukum/notaris |
| **5. Labeling Produk & Stiker** | Stiker Vinyl A3+ Kiss Cut & Die Cut (Laminasi Doff/Glossy), Stiker Transparan, Stiker Kromo, UV Flatbed | UMKM kuliner kemasan, botol minuman herbal, kosmetik/skincare lokal, frozen food | Postingan peluncuran varian produk baru, toples/botol tanpa label merk di foto profil |

---

## 3. Matriks Integrasi Alat Bantu Perayapan Bebas Biaya (GitHub MIT)

Untuk menghilangkan ketergantungan biaya Apify Cloud, sistem menggunakan 6 repositori open-source MIT lokal:

| Nama Modul / Repositori | Lisensi | Fungsi Pengayaan Spesifik | Muara Data di Sistem |
|---|---|---|---|
| **`omkarcloud/google-maps-scraper`** | MIT | Panen massal seluruh sektor di Makassar (sekolah, notaris, distro, klinik, kafe) tanpa kuota Apify. Mengambil ulasan teks penuh dan koordinat GPS. | Tabel `locations`, `digital_footprints`, dan `service_needs` |
| **`Nv7-GitHub/googlesearch`** | MIT | Menjalankan *Google Dorking* otomatis untuk direktori publik sekolah (`site:sch.id makassar`) dan kepanitiaan acara kota Makassar. | Tabel `entities.sector = 'education'/'event'` |
| **`subzeroid/instagrapi`** | MIT | Mengekstrak nomor WhatsApp resmi dari tombol kontak bisnis profil Instagram dan 5 postingan mutakhir akun komunitas/brand. | Tabel `entities.whatsapp_number`, tabel `channel_posts` |
| **`extract-social-media`** | MIT | Menelusuri tautan website/Linktree yang ditemukan di Google Maps untuk mengekstrak handle IG, link TikTok, dan tombol WhatsApp alternatif. | Relasi data silang Maps menuju akun media sosial |
| **`athm793/meta-ads-scraper`** | MIT | Memantau Meta Ads Library untuk mendeteksi brand lokal yang aktif beriklan digital (ditandai sebagai Prospek Tier A belanja materi promosi fisik). | `digital_footprints.has_meta_ads = 1` |
| **`FahadMAlsamiti/WhatsappChecker`** | MIT | Memverifikasi nomor telepon hasil perayapan sebelum outreach sales (membuang nomor telepon kabel PSTN dan nomor tidak aktif). | `entities.is_wa_valid = 1`, akurasi kontak >85% |

---

## 4. Matriks Pemetaan Titik Data Lengkap (Data Placement Matrix)

| Titik Data Asli | Tipe Data | Penempatan di SQLite (`data/leads.sqlite`) | Penempatan di CSV Full | Tampilan di Dashboard UI |
|---|---|---|---|---|
| `entity_id` | String | `entities.entity_id` | Kolom `entity_id` | ID Entitas Prospek |
| `business_name` | String | `entities.business_name` | Kolom `business_name` | Judul Kartu & Drawer Modal |
| `target_sector` | String | `entities.target_sector` | Kolom `target_sector` | Badge Sektor (Pendidikan / Korporat / Event / Retail / F&B) |
| `primary_service_pillar` | String | `entities.primary_service_pillar` | Kolom `primary_service_pillar` | Badge 5 Pilar Layanan |
| `whatsapp_number` | String | `entities.whatsapp_number` | Kolom `whatsapp_number` | Tombol Utama Hubungi WhatsApp |
| `is_wa_valid` | Boolean | `entities.is_wa_valid` | Kolom `is_wa_valid` | Indikator Centang Hijau Verifikasi WA |
| `address_full` | String | `locations.address_full` | Kolom `address_full` | Lokasi Outlet / Kantor Fisik |
| `district_area` | String | `locations.district_area` | Kolom `district_area` | Filter Wilayah Kecamatan |
| `sales_cluster` | String | `locations.sales_cluster` | Kolom `sales_cluster` | Rute Cluster Sales Lapangan |
| `latitude`, `longitude` | Float | `locations.latitude`, `locations.longitude` | Kolom `latitude`, `longitude` | Titik Pin Peta Rute Sales |
| `place_id` | String | `locations.place_id` | Kolom `place_id` | Tautan Verifikasi Lokasi Google Maps |
| `website_url` | String | `digital_footprints.website_url` | Kolom `website_url` | Tautan Web / Landing Page / Linktree |
| `gmaps_rating` | Float | `digital_footprints.gmaps_rating` | Kolom `gmaps_rating` | Indikator Bintang Reputasi |
| `gmaps_reviews_count` | Integer | `digital_footprints.gmaps_reviews_count` | Kolom `gmaps_reviews_count` | Total Jumlah Ulasan Konsumen |
| `review_snippets_json` | JSON List | `digital_footprints.review_snippets_json` | Kolom `review_samples` | Tab Ulasan Pelanggan |
| `instagram_handle` | String | `digital_footprints.instagram_handle` | Kolom `instagram_handle` | Tautan Profil Instagram |
| `instagram_followers` | Integer | `digital_footprints.instagram_followers` | Kolom `instagram_followers` | Indikator Jangkauan Audiens |
| `latest_post_date` | Date/ISO | `digital_footprints.latest_post_date` | Kolom `latest_post_date` | Status Keaktifan Usaha (<30 Hari) |
| `has_meta_ads` | Boolean | `digital_footprints.has_meta_ads` | Kolom `has_meta_ads` | Status Iklan Berbayar Aktif |
| `lead_score` | Integer (0-100)| `commercial_intelligence.lead_score` | Kolom `lead_score` | Skor Prospek Terpadu (CMYK) |
| `priority_tier` | String (A/B/C/D)| `commercial_intelligence.priority_tier` | Kolom `tier` | Badge Prioritas Tindak Lanjut Sales |
| `score_legitimacy` | Integer (0-25)| `commercial_intelligence.score_legitimacy` | Kolom `score_legitimacy` | Bilah Progres Pilar Legitimasi Fisik |
| `score_velocity` | Integer (0-25)| `commercial_intelligence.score_velocity` | Kolom `score_velocity` | Bilah Progres Pilar Kecepatan Aktivitas |
| `score_turnover` | Integer (0-30)| `commercial_intelligence.score_turnover` | Kolom `score_turnover` | Bilah Progres Pilar Nilai Pengadaan |
| `score_budget` | Integer (0-20)| `commercial_intelligence.score_budget` | Kolom `score_budget` | Bilah Progres Pilar Anggaran Promosi |
| `detected_service_needs` | JSON List | `commercial_intelligence.detected_service_needs` | Kolom `detected_service_needs` | Tag Kebutuhan Cetak Spesifik |
| `service_pain_points` | JSON List | `commercial_intelligence.service_pain_points` | Kolom `service_pain_points` | Keluhan Mutu Percetakan Sebelumnya |
| `est_order_value_idr` | Integer | `commercial_intelligence.est_order_value_idr` | Kolom `est_order_value_idr` | Estimasi Nilai Transaksi Potensial (IDR) |
| `recommended_products` | String | `commercial_intelligence.recommended_products` | Kolom `recommended_products` | Produk Unggulan Katalog Terkait |
| `whatsapp_pitch` | String | `outreach_logs.whatsapp_pitch` | Kolom `whatsapp_pitch` | Draf Pesan Penawaran Personal |
| `outreach_status` | String | `outreach_logs.outreach_status` | Kolom `sales_status` | Dropdown Status CRM Sales |
| `sales_notes` | String | `outreach_logs.sales_notes` | Kolom `sales_notes` | Catatan Lapangan Tim Sales |

---

## 5. DDL Skema Basis Data SQLite Terstruktur (`data/leads.sqlite`)

```sql
-- 1. Master Entitas Calon Pelanggan Lintas Sektor
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    business_name TEXT NOT NULL,
    target_sector TEXT NOT NULL,           -- education, corporate_legal, event_community, retail_apparel, fnb_hospitality
    primary_service_pillar TEXT NOT NULL,  -- advertising, custom_merch, apparel, office_school, label_sticker
    category_raw TEXT,
    whatsapp_number TEXT,
    phone_raw TEXT,
    is_wa_valid INTEGER DEFAULT 0,
    is_commercial INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Detail Lokasi Fisik dan Geografis
CREATE TABLE IF NOT EXISTS locations (
    entity_id TEXT PRIMARY KEY,
    place_id TEXT,
    address_full TEXT,
    district_area TEXT,
    city TEXT DEFAULT 'makassar',
    sales_cluster TEXT,
    latitude REAL,
    longitude REAL,
    opening_hours_json TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

-- 3. Jejak Multi-Kanal Digital
CREATE TABLE IF NOT EXISTS digital_footprints (
    entity_id TEXT PRIMARY KEY,
    website_url TEXT,
    gmaps_rating REAL,
    gmaps_reviews_count INTEGER DEFAULT 0,
    review_snippets_json TEXT,
    instagram_handle TEXT,
    instagram_bio TEXT,
    instagram_followers INTEGER DEFAULT 0,
    latest_post_date TEXT,
    tiktok_handle TEXT,
    has_meta_ads INTEGER DEFAULT 0,
    meta_ads_data_json TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

-- 4. Intelijen Komersial & Kebutuhan Cetak/Konveksi
CREATE TABLE IF NOT EXISTS commercial_intelligence (
    entity_id TEXT PRIMARY KEY,
    lead_score INTEGER DEFAULT 0,
    priority_tier TEXT DEFAULT 'Tier D',
    score_legitimacy INTEGER DEFAULT 0,
    score_velocity INTEGER DEFAULT 0,
    score_turnover INTEGER DEFAULT 0,
    score_budget INTEGER DEFAULT 0,
    detected_service_needs TEXT,           -- JSON array kebutuhan cetak
    service_pain_points TEXT,              -- keluhan mutu vendor lama
    est_order_value_idr INTEGER DEFAULT 0,
    recommended_products TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

-- 5. Cache Konten & Pemicu Promosi
CREATE TABLE IF NOT EXISTS channel_posts (
    post_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    caption TEXT,
    posted_at TEXT,
    engagement_rate REAL DEFAULT 0.0,
    service_trigger_signal TEXT,          -- PPDB, sponsorship, event, new menu, jersey
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

-- 6. Log Outreach dan Pelacakan CRM Penjualan
CREATE TABLE IF NOT EXISTS outreach_logs (
    entity_id TEXT PRIMARY KEY,
    outreach_status TEXT DEFAULT 'Belum Dihubungi',
    whatsapp_pitch TEXT,
    sales_notes TEXT,
    contacted_at TEXT,
    last_followup_at TEXT,
    sales_rep_name TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

-- Indeks Kueri Cepat
CREATE INDEX IF NOT EXISTS idx_entities_sector ON entities(target_sector);
CREATE INDEX IF NOT EXISTS idx_entities_pillar ON entities(primary_service_pillar);
CREATE INDEX IF NOT EXISTS idx_intelligence_tier ON commercial_intelligence(priority_tier);
CREATE INDEX IF NOT EXISTS idx_intelligence_score ON commercial_intelligence(lead_score);
CREATE INDEX IF NOT EXISTS idx_locations_cluster ON locations(sales_cluster);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_logs(outreach_status);
```

---

## 6. Format Ekspor CSV Lengkap (`data/processed/dossiers_export_full.csv`)

Berkas ekspor lengkap memuat 32 kolom baku:
1. `entity_id`
2. `business_name`
3. `target_sector`
4. `primary_service_pillar`
5. `category_raw`
6. `priority_tier`
7. `lead_score`
8. `score_legitimacy`
9. `score_velocity`
10. `score_turnover`
11. `score_budget`
12. `detected_service_needs`
13. `service_pain_points`
14. `est_order_value_idr`
15. `recommended_products`
16. `address_full`
17. `district_area`
18. `sales_cluster`
19. `latitude`
20. `longitude`
21. `place_id`
22. `gmaps_rating`
23. `gmaps_reviews_count`
24. `review_samples`
25. `website_url`
26. `instagram_handle`
27. `whatsapp_number`
28. `is_wa_valid`
29. `has_meta_ads`
30. `whatsapp_pitch`
31. `sales_status`
32. `sales_notes`

---

## 7. Desain 4 Tab Drawer Modal Dashboard Terpadu

Antarmuka `/market-scraping` menampilkan 4 tab komprehensif:

```
+-------------------------------------------------------------------------+
| [HEADER] Nama Entitas — Sektor & Pilar Layanan — Badge Tier & Skor CMYK |
+-------------------------------------------------------------------------+
| [TAB 1: KONTAK & PITCH PENJUALAN]                                       |
| - Tombol WhatsApp Valid (dengan status verifikasi nomor aktif)          |
| - Alamat Kantor/Sekolah/Toko, Kecamatan & Cluster Rute Sales            |
| - Draf WhatsApp Pitch Spesifik Sektor (Map Raport / Kaos DTF / Reklame) |
| - Status Outreach CRM Penjualan & Kolom Catatan Sales                   |
+-------------------------------------------------------------------------+
| [TAB 2: INTELIJEN LAYANAN & ESTIMASI NILAI ORDER]                       |
| - Rincian Bobot Skor 4 Pilar (0-100)                                     |
| - Kebutuhan Layanan Terdeteksi (Spanduk, Kaos, Ganci Akrilik, Map, dll)|
| - Estimasi Potensi Transaksi (IDR) & Rekomendasi Katalog Terkait        |
+-------------------------------------------------------------------------+
| [TAB 3: ULASAN PUBLIK & TEMUAN KELUHAN MUTU]                            |
| - Rating Google Maps & Volume Ulasan                                    |
| - Deteksi Keluhan Percetakan Lama (Warna pudar, telat, jahitan, sobek)  |
| - Sampel Cuplikan Ulasan Konsumen Asli                                  |
+-------------------------------------------------------------------------+
| [TAB 4: JEJAK MULTI-KANAL & MATERI PROMOSI]                            |
| - Tautan Situs Web / Direktori Sekolah / Linktree                       |
| - Profil Instagram, Jumlah Pengikut, dan Tanggal Unggahan Mutakhir     |
| - Status Kampanye Iklan Berbayar Meta Ads                               |
| - Sinyal Pemicu Konten (Dies Natalis, PPDB, Grand Opening, Seragam Baru)|
+-------------------------------------------------------------------------+
```

---

## 8. Aturan Mutlak Format & Keamanan
1. **Bebas Emoji Mutlak**: Seluruh kolom basis data, berkas CSV, log terminal, antarmuka dashboard, dan draf pesan wajib 100% bebas dari emoji dan simbol emotikon.
2. **Zero-Interference Guardrails**: Tetap dilarang keras melakukan operasi tulis/mutasi ke basis data produksi Supabase. Seluruh data prospek disimpan terisolasi di `data/leads.sqlite` dan `data/processed/`.
3. **Standar Efisiensi Kode (Ponytail Lean Code)**: Mengutamakan modul bawaan Python (`sqlite3`, `json`, `csv`, `pathlib`) tanpa overhead pustaka yang tidak esensial.
