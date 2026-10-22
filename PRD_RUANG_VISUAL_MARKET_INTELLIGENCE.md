# PRD — RUANG VISUAL Market Intelligence & Autonomous B2B Prospecting Engine

Dokumen Spesifikasi Persyaratan Produk (PRD) Skala Enterprise dan Panduan Arsitektur Teknis
Versi: 2.0 (Comprehensive Architecture Release)
Status: Dokumen Kerja Arsitektur (Siap Audit & Implementasi)
Klasifikasi: Internal — Divisi Teknologi & Marketing RUANG VISUAL
Arsitek: Antigravity (Architect, Auditor & Integrator)
Pelaksana: Kilo (Builder & Scraper Specialist)

---

## 1. Visi Strategis, Latar Belakang & Model Ekonomi Bisnis

### 1.1 Pernyataan Masalah (Problem Statement)
Sistem scraping terdahulu mengoperasikan skrip pencarian teks acak pada platform publik tanpa verifikasi kontekstual (*blind scraping*). Dampak sistemik yang terjadi:
1. **Pencemaran Data (Data Toxicity)**: Lebih dari 65% data yang masuk ke Google Sheets adalah akun mati, bisnis gulung tikar, atau akun pribadi tanpa kebutuhan cetak.
2. **Ketiadaan Validitas Kontak**: Sebagian besar entitas tidak memiliki nomor WhatsApp yang dapat dihubungi secara langsung, memaksa tim sales melakukan pencarian manual yang tidak efisien.
3. **Keterbatasan Format Flat Spreadsheet**: Google Sheets mengalami penurunan performa saat menampung ribuan baris data relasional, tidak mendukung *state management* alur penjualan (pipeline CRM), dan rentan mengalami kerusakan skema (*schema drift*).
4. **Resiko Pemblokiran IP**: Skrip perayap lokal yang rapuh memicu pemblokiran alamat IP secara berkala dari platform Meta dan Google.

### 1.2 Visi Sistem (The Autonomous B2B Printing Flywheel)
RUANG VISUAL Market Intelligence Engine adalah platform terintegrasi yang mentransformasi fungsi pemasaran dari pencarian reaktif menjadi **mesin akuisisi dan retensi pelanggan B2B otomatis**. Sistem bekerja dengan menjaring sinyal kebutuhan cetak komersial secara *multi-vector*, memvalidasi keaktifan akun secara ketat, memetakan katalog produk secara cerdas, dan memfasilitasi interaksi penjualan berkonversi tinggi melalui aplikasi web lokal mandiri berstandar UI CMYK RUANG VISUAL.

### 1.3 Model Matematika Konversi & Unit Economics
Sistem dirancang untuk mencapai efisiensi biaya akuisisi pelanggan (Customer Acquisition Cost / CAC) dan memaksimalkan nilai seumur hidup pelanggan (Lifetime Value / LTV):

$$\text{Lead Quality Index (LQI)} = \sum (W_{\text{kontak}} \cdot S_{\text{kontak}} + W_{\text{aktif}} \cdot S_{\text{aktif}} + W_{\text{anggaran}} \cdot S_{\text{anggaran}} + W_{\text{lokasi}} \cdot S_{\text{lokasi}})$$

- **Biaya Ekstraksi per Prospek Tervalidasi**: Ditargetkan di bawah Rp 150,- per entitas bisnis (memanfaatkan kombinasi mesin gratis lokal dan alokasi kuota Apify Free Tier $5/bulan).
- **Rasio Konversi Target**:
  - Raw Scraping -> Verified Active Leads: 30% - 40%.
  - Verified Leads -> WhatsApp Outreach Sent: 85%.
  - Outreach -> Request Quotation / Sample Box: 15% - 22%.
  - Sample Box Sent -> Paid B2B Customer (Deal): 35% - 50%.
- **Siklus Pembelian Berulang (Repeat Order Velocity)**:
  - F&B Packaging: Siklus restock 25 - 40 hari.
  - Retail & Fashion Branding: Siklus restock 45 - 60 hari.

---

## 2. Peta Dokumen & Diagram Arsitektur

Dokumentasi grafis dan rincian teknis disimpan secara terstruktur di dalam repositori:

1. **Diagram Alur Rinci Multi-Platform (Resolusi Tinggi)**:
   [docs/flowcharts/flowchart_multiplatform_scraping_detailed.png](file:///Users/muhammadfanani/Documents/2026%20COMMISSION/RUANG%20VISUAL/DATA%20CALON%20CUSTOMER/docs/flowcharts/flowchart_multiplatform_scraping_detailed.png)
   Memetakan aliran 5 lajur ekstraksi data (Instagram, Google Maps, TikTok, Meta Ads, Food Delivery) hingga ke mesin verifikasi dan Supabase.
2. **Dokumen Spesifikasi Titik Data Ekstraksi**:
   [docs/flowcharts/DETAIL_EKSTRAKSI_MULTIPLATFORM.md](file:///Users/muhammadfanani/Documents/2026%20COMMISSION/RUANG%20VISUAL/DATA%20CALON%20CUSTOMER/docs/flowcharts/DETAIL_EKSTRAKSI_MULTIPLATFORM.md)
   Menjelaskan struktur data mentah dan field spesifik tiap platform.
3. **Diagram Pipeline Makro**:
   [docs/flowcharts/flowchart_high_level_pipeline.png](file:///Users/muhammadfanani/Documents/2026%20COMMISSION/RUANG%20VISUAL/DATA%20CALON%20CUSTOMER/docs/flowcharts/flowchart_high_level_pipeline.png)

---

## 3. Matriks Sektor Usaha vs Taksonomi Produk Cetak RUANG VISUAL

Sistem penalaran produk (*Product Need Inference Engine*) membedah profil calon pelanggan ke dalam taksonomi produk cetak terperinci berdasarkan aturan leksikal dan klasifikasi visual:

| Sektor Usaha Target | Kamus Kata Kunci Profil / Unggahan | Taksonomi Produk Cetak RUANG VISUAL | Spesifikasi Bahan Baku & Finishing | Sudut Penawaran Nilai (Value Proposition) |
| :--- | :--- | :--- | :--- | :--- |
| **F&B: Coffee Shop & Minuman** | coffee, cafe, roastery, kopi, espresso, artisan, boba, tea, brew, latte, matcha | Paper Cup Hot 8oz/12oz, Cup Cold PET/PP, Cup Sleeve Kraft, Coaster/Tatakan Gelas, Buku Menu Meja, Stiker Segel Toples | Kraft PE Coating anti-rembes, Sablon presisi 1-4 warna, Ivory 300gsm laminasi doff anti-air | Desain estetik kekinian, tahan embun es dan panas kopi, menjaga aroma kopi tetap prima. |
| **F&B: Restoran & Katering** | resto, restaurant, catering, dapur, bento, sambal, seafood, ayam, kitchen, ricebox | Paper Lunch Box Formed (M/L), Food Pail, Wrapping Paper Makanan Custom, Kantong Kresek Singkong / Paper Bag Takeaway | Brown Kraft / Ivory Food Grade 290gsm, Tinta bersertifikasi FDA aman untuk makanan panas berminyak | Kemasan higienis berstandar food-grade, kemasan tidak bocor kuah/minyak, branding mewah. |
| **Fashion & Boutique** | butik, boutique, clothing, apparel, fashion, hijab, thrift, outfit, wear, kebaya | Hangtag Baju Tebal, Kartu Ucapan Terima Kasih (Thank You Card), Polymailer Cetak Logo, Shopping Bag / Paper Bag Tali Kur | Art Carton 360gsm/400gsm, Laminasi Doff Velvet, Hotprint Foil Emas/Perak, Emboss Logo timbul | Meningkatkan gengsi pakaian, membuat harga jual baju terlihat layak dihargai mahal oleh konsumen. |
| **Kecantikan & Skincare** | clinic, aesthetic, beauty, skincare, facial, spa, dokter gigi, serum, herbal, glowing | Stiker Segel Botol Jar Transparan / Vinyl, Box Lipat Skincare Kosmetik, Brosur Panduan Perawatan Lipat 3 | Vinyl Glossy White / Transparan Camel, Duplex/Ivory 310gsm + Finishing UV Spot lokal bertekstur | Stiker tahan gores dan tidak pudar terkena minyak/cairan kimia serum, warna cetak presisi konsisten. |
| **Outlet Komersial Baru (Opening Soon)** | opening soon, grand opening, hadir di, new branch, cabang baru, segera hadir, soft launch | Signage Akrilik Toko, Neon Box LED Custom, Stiker Kaca One-Way Vision, Spanduk Kain Banner Outdoor, X/Y-Banner | Flexi Jerman 510gsm outdoor tahan cuaca, Stiker Ritrama + Laminating UV, Akrilik Marga Cipta 3mm | Pengerjaan kilat siap sebelum hari pembukaan resmi, warna spanduk tajam terbaca dari kejauhan. |
| **Korporat, Notaris & Event** | notaris, ppat, law firm, wedding organizer, seminar, property, konsultan, yayasan | Map Berkas Folder Dokumen (Kantong Dalam), Nota / Surat Jalan NCR 2-4 Ply, ID Card PVC + Lanyard Sablon, Sertifikat | Art Carton 310gsm laminasi satu sisi, Kertas NCR Carbonless tulisan tembus jelas, PVC tebal 0.76mm | Citra formal kredibel, kerapian jilid arsip hukum, kertas NCR berkualitas tidak mengotori tangan. |

---

## 4. Arsitektur Ekstraksi Data Multi-Platform (Multi-Vector Engine)

Sistem menggunakan model hibrida: **In-House Engine (Crawlee & TLS-Client Lokal)** untuk tugas rutin, dan **Apify Cloud Actor** untuk operasi massal berisiko tinggi.

```
                    +------------------------------------+
                    |   Pusat Kendali Kampanye (Next.js) |
                    +------------------------------------+
                                      |
                      [Router Berdasarkan Vektor Target]
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
[In-House Engine (Gratis / Lokal)]                       [Apify Cloud API (Token Terkelola)]
- Google Maps Compass Parser                             - Instagram Massive Followers Spider
- Threads Keyword Monitor                                - Meta Ads Library Comprehensive Harvester
- Facebook Marketplace Harvester                         - TikTok Profile & Live Stream Extractor
- Food Apps Merchant Directory Scraper
         |                                                         |
         +----------------------------+----------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |   Data Normalization & Deduplicator|
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |  Cross-Platform Entity Matcher     |
                    | (Fuzzy Matching Jaro-Winkler)      |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    | Verification Guard:                |
                    | 1. Recency < 30 Hari               |
                    | 2. Normalisasi WA 628xxx           |
                    | 3. Lead Scoring Engine (1 - 100)   |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    | Supabase PostgreSQL Storage        |
                    +------------------------------------+
```

### 4.1 Spesifikasi Rinci per Platform

#### A. Instagram (Social & Business Identity Vector)
- **Engine**: `apify/instagram-profile-scraper` (Apify Cloud Actor wajib) atau library Python `instagrapi` dengan sesi akun bot.
- **Catatan Teknis Kritikal**: Data `business_phone_number` dari tombol kontak profil bisnis Instagram TIDAK dapat diakses melalui Crawlee atau Playwright yang merender halaman HTML publik. Data tombol kontak hanya tersedia melalui internal API Meta yang memerlukan sesi terautentikasi. Kilo wajib menggunakan Apify Actor atau `instagrapi`, bukan Playwright/Crawlee tanpa sesi.
- **Titik Data yang Diambil**:
  - `username`, `full_name`, `biography`, `external_url`.
  - `business_category_name`, `business_email`, `business_phone_number`.
  - `followers_count`, `follows_count`, `media_count`.
  - `latest_post_timestamps` (Array 3 postingan terakhir).
  - `caption_text` dan `comment_count`.
- **Aturan Ekstraksi WhatsApp (Urutan Prioritas)**:
  1. Ambil `business_phone_number` dari metadata tombol kontak (via Apify Actor / instagrapi).
  2. Jika kosong, lakukan pemindaian regex pada `biography` dan `external_url` (Linktree, biolinky, bit.ly, wa.me).
  3. Format seluruh nomor ke standar `628xxxxxxxxxx`.

#### B. Google Maps (Physical Location & Competitor Weakness Vector)
- **Engine**: In-House Compass Parser & `compass/crawler-google-places`.
- **Titik Data yang Diambil**:
  - `place_id`, `title`, `category_name`, `sub_categories`.
  - `address`, `neighborhood`, `city`, `postal_code`, `location` (latitude, longitude).
  - `phone_number` (dibersihkan dan diverifikasi).
  - `website`, `price_level`, `opening_hours`.
  - `reviews_count`, `total_score` (rating bintang).
  - `negative_reviews`: Ulasan bintang 1-3 khusus percetakan kompetitor.
- **Logika Celah Kompetitor**:
  Sistem mengekstrak kata kunci keluhan dari ulasan kompetitor: "buruk", "luntur", "telat", "salah potong", "pudar", "robek". Keluhan ini dimasukkan ke tabel `lead_insights` sebagai amunisi sales untuk menawarkan solusi jaminan kualitas RUANG VISUAL.

#### C. Meta Ads Library (Active Commercial Budget Vector)
- **Engine**: `apify/facebook-ads-scraper` terintegrasi dengan Meta Ad Archive Endpoint.
- **Titik Data yang Diambil**:
  - `page_name`, `page_id`, `ad_creation_time`.
  - `ad_creative_body` (isi teks iklan), `ad_snapshot_url`.
  - `cta_type` (contoh: "Send WhatsApp Message", "Shop Now").
  - `destination_url` (landing page tujuan).
- **Logika Penilaian**: Bisnis yang memiliki iklan berbayar aktif memiliki likuiditas kas operasional. Prospek dari jalur ini otomatis mendapatkan skor bobot anggaran tertinggi.

#### D. TikTok (Live Commerce & Packaging Volume Vector)
- **Engine**: `clockworks/tiktok-profile-scraper` dan hashtag harvester.
- **Titik Data yang Diambil**:
  - `author_unique_id`, `nickname`, `signature` (bio).
  - `bio_link`, `follower_count`, `heart_count`.
  - `is_commerce_user` (indikator akun toko), `recent_video_captions`.
- **Kualifikasi Seller Aktif**: Akun yang mencantumkan link toko online atau rutin melakukan live streaming pengiriman barang ditandai sebagai konsumen potensial untuk stiker resi thermal dan kemasan kardus.

#### E. Food Delivery Apps (ShopeeFood, GoFood, GrabFood)
- **Engine**: In-House Directory Scraper.
- **Titik Data yang Diambil**:
  - `brand_name`, `branch_name`, `merchant_category`, `cuisine_type`.
  - `menu_photo_urls` (analisis kemasan visual).
- **Algoritma Pencocokan Entitas Lintas Platform (Entity Matcher)**:
  Karena aplikasi pengantaran makanan mengenkripsi nomor telepon, sistem menjalankan pencarian terotomasi:
  1. Kueri pencarian: `"[brand_name] [branch_name] [city] instagram"`.
  2. Hitung kemiripan string menggunakan algoritma Jaro-Winkler:
     $$\text{Similarity}(\text{Brand}_{\text{Food}}, \text{Brand}_{\text{IG}}) \ge 0.85$$
  3. **Disambiguasi wajib**: Jika kemiripan >= 0.85 menghasilkan lebih dari satu kandidat, gunakan kecamatan/kelurahan dari data restoran sebagai parameter pembanding sekunder. Jika setelah disambiguasi masih terdapat lebih dari satu kandidat yang cocok, tandai status lead sebagai `requires_manual_review` dan jangan masukkan data ke tabel `leads` secara otomatis.
  4. Jika terverifikasi cocok (satu kandidat tunggal), ekstrak nomor WhatsApp dan profil Instagram bisnis tersebut.

---

## 5. Algoritma Verifikasi Data & Perhitungan Skor Prospek (Lead Scoring Engine)

Setiap entitas prospek yang terjaring wajib melewati dua gerbang penilaian:

### 5.1 Gerbang Kualifikasi Mutlak (Hard Filters)
Prospek akan langsung dibuang atau ditandai *Dropped* jika memenuhi salah satu kondisi berikut:
1. **Aturan Keaktifan (< 30 Hari)**:
   $$\text{Hari Sejak Post Terakhir} > 30 \implies \text{Status} = \text{Non-Aktif (Gugur)}$$
2. **Ketiadaan Kontak**: Tidak ditemukan nomor telepon kantor maupun nomor WhatsApp bisnis.
3. **Akun Anonim / Pribadi**: Tidak ditemukan indikasi kata kunci komersial pada profil, bio, nama usaha, atau kategori produk.

### 5.2 Formula Penghitungan Skor Kualitas Prospek (Lead Score 1 - 100)

> CATATAN: Definisi skor di bab ini adalah satu-satunya sumber kebenaran (Single Source of Truth). Seluruh modul dan dokumen lain harus merujuk ke sini, bukan mendefinisikan ulang.

Skor prospek dihitung secara deterministik menggunakan fungsi berikut:

$$\text{raw\_score} = S_{\text{kontak}} + S_{\text{keaktifan}} + S_{\text{lokasi}} + S_{\text{anggaran}} + S_{\text{skala}}$$

$$\text{final\_score} = \min(\text{raw\_score},\; 100)$$

Nilai `final_score` tidak boleh melebihi 100 dalam kondisi apa pun, meskipun seluruh komponen terpenuhi secara bersamaan.

Dengan rincian komponen:

1. **Komponen Kontak ($S_{\text{kontak}}$, Maksimal 30 Poin)**:
   - Memiliki nomor WhatsApp bisnis valid: 30 poin.
   - Hanya memiliki nomor telepon kantor tetap: 15 poin.
   - Hanya memiliki alamat email: 5 poin.
2. **Komponen Keaktifan ($S_{\text{keaktifan}}$, Maksimal 25 Poin)**:
   - Unggahan terakhir <= 3 hari yang lalu: 25 poin.
   - Unggahan terakhir <= 7 hari yang lalu: 20 poin.
   - Unggahan terakhir <= 14 hari yang lalu: 15 poin.
   - Unggahan terakhir <= 30 hari yang lalu: 10 poin.
3. **Komponen Lokasi Fisik ($S_{\text{lokasi}}$, Maksimal 20 Poin)**:
   - Terdaftar di Google Maps dengan alamat fisik terverifikasi: 20 poin.
   - Alamat terdeteksi di teks bio tanpa koordinat: 10 poin.
4. **Komponen Sinyal Anggaran ($S_{\text{anggaran}}$, Maksimal 15 Poin)**:
   - Sedang aktif menjalankan Meta Ads (Facebook/Instagram Ads): 15 poin.
   - Menggunakan domain website berbayar mandiri (bukan free blog): 10 poin.
5. **Komponen Skala Usaha ($S_{\text{skala}}$, Maksimal 10 Poin)**:
   - Pengikut media sosial antara 1.000 hingga 50.000 (Target Sweet-Spot UMKM Berkembang): 10 poin.
   - Pengikut antara 500 hingga 999: 5 poin.
   - Pengikut > 100.000 (Korporasi besar dengan vendor pusat tetap): 3 poin.

---

## 6. Skema Lengkap Database Supabase (PostgreSQL DDL)

Skema relasional ini menggantikan lembar kerja spreadsheet dan dirancang untuk skalabilitas hingga jutaan data:

```sql
-- ============================================================================
-- RUANG VISUAL — MARKET INTELLIGENCE RELATIONAL DATABASE SCHEMA
-- Target Engine: PostgreSQL 15+ / Supabase
-- ============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Untuk fuzzy matching pencarian nama usaha

-- 2. ENUMS
CREATE TYPE platform_type AS ENUM (
    'instagram', 
    'google_maps', 
    'tiktok', 
    'facebook_ads', 
    'facebook_marketplace', 
    'threads', 
    'shopee_food', 
    'go_food', 
    'grab_food'
);

CREATE TYPE business_category_type AS ENUM (
    'fnb_beverage',
    'fnb_food_resto',
    'fashion_retail',
    'beauty_skincare',
    'corporate_legal',
    'event_service',
    'new_store_opening',
    'general_commercial'
);

CREATE TYPE outreach_status_type AS ENUM (
    'new_lead',
    'ready_to_pitch',
    'contacted',
    'sample_box_requested',
    'sample_box_dispatched',
    'sample_delivered',
    'quotation_sent',
    'negotiation',
    'won_deal',
    'lost_declined',
    'unresponsive',
    'blacklisted'
);

CREATE TYPE scraper_engine_type AS ENUM (
    'in_house_crawlee',
    'in_house_direct_api',
    'apify_cloud_actor'
);

-- 3. TABLE: target_sources
-- Menyimpan daftar sumber kampanye (misal: "Pengikut @bazar_makassar", "Resto Baru Panakkukang")
CREATE TABLE target_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name VARCHAR(255) NOT NULL,
    platform platform_type NOT NULL,
    target_handle_or_query VARCHAR(255) NOT NULL,
    target_type VARCHAR(100) NOT NULL, -- 'followers', 'following', 'hashtag', 'radius_geo', 'ad_archive'
    engine_used scraper_engine_type DEFAULT 'in_house_crawlee',
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    total_raw_found INTEGER DEFAULT 0,
    total_qualified_leads INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. TABLE: leads
-- Entitas inti calon pelanggan B2B RUANG VISUAL
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES target_sources(id) ON DELETE SET NULL,
    business_name VARCHAR(255) NOT NULL,
    category business_category_type NOT NULL DEFAULT 'general_commercial',
    platform platform_type NOT NULL,
    platform_profile_url TEXT,
    platform_handle VARCHAR(150),
    platform_id VARCHAR(150),
    
    -- Validasi Kontak
    whatsapp_number VARCHAR(30), -- Format bersih: 628xxxxxxxxxx
    phone_office VARCHAR(50),
    email_address VARCHAR(150),
    
    -- Lokasi & Alamat Fisik (Krusial untuk Pengiriman Sampel Bahan)
    address_full TEXT,
    district_area VARCHAR(100),
    city VARCHAR(100) DEFAULT 'Makassar',
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    google_maps_place_id VARCHAR(255),
    
    -- Metrik Aktivitas & Keaktifan (Anti-Blind Scraping Guard)
    follower_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    latest_post_date TIMESTAMP WITH TIME ZONE,
    -- CATATAN: days_since_latest_post tidak disimpan sebagai kolom statis karena akan
    -- menjadi stale. Nilai ini dihitung dinamis di query: (CURRENT_DATE - latest_post_date::date).
    is_active_verified BOOLEAN DEFAULT FALSE,
    is_ad_active BOOLEAN DEFAULT FALSE,
    external_website_url TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. TABLE: lead_insights
-- Mesin penalar kebutuhan cetak dan nilai intelijen bisnis
CREATE TABLE lead_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID UNIQUE REFERENCES leads(id) ON DELETE CASCADE,
    lead_score INTEGER NOT NULL CHECK (lead_score >= 0 AND lead_score <= 100),
    projected_products TEXT[] NOT NULL DEFAULT '{}', -- Contoh: ARRAY['Paper Cup 12oz', 'Cup Sleeve Kraft', 'Stiker Vinyl']
    matched_keywords TEXT[] DEFAULT '{}',
    custom_pitch_hook TEXT, -- Template draf pembuka chat yang dipersonalisasi
    competitor_reference TEXT, -- Celah dari percetakan yang pernah mereka pakai
    qualification_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. TABLE: crm_outreach
-- Pelacak eksekusi tim sales, alur negosiasi, dan pengiriman sampel fisik
CREATE TABLE crm_outreach (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID UNIQUE REFERENCES leads(id) ON DELETE CASCADE,
    status outreach_status_type NOT NULL DEFAULT 'new_lead',
    
    -- Sample Box Physical Touchpoint
    sample_box_requested BOOLEAN DEFAULT FALSE,
    sample_box_type VARCHAR(100), -- 'fnb_packaging_kit', 'apparel_hangtag_kit', 'corporate_kit'
    sample_box_tracking_number VARCHAR(100),
    sample_box_courier VARCHAR(50),
    sample_delivered_at TIMESTAMP WITH TIME ZONE,
    
    -- Penawaran & Transaksi
    quotation_number VARCHAR(100),
    quotation_value NUMERIC(14, 2) DEFAULT 0,
    won_deal_value NUMERIC(14, 2) DEFAULT 0,
    projected_repeat_order_days INTEGER, -- Estimasi siklus habis kemasan (misal: 30 hari)
    next_follow_up_date DATE,
    
    -- Riwayat Interaksi
    interaction_history JSONB DEFAULT '[]'::jsonb,
    sales_agent_assigned VARCHAR(100),
    last_contacted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. TABLE: competitor_matrix
-- Analisis kelemahan percetakan pesaing untuk penetrasi pasar
-- Diisi oleh modul Google Maps Negative Review Scraper dari Bab 4.1.B
CREATE TABLE competitor_matrix (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES target_sources(id) ON DELETE SET NULL, -- Sumber kampanye scraping yang menghasilkan data ini
    competitor_name VARCHAR(255) NOT NULL,
    google_maps_place_id VARCHAR(255),
    average_rating NUMERIC(3, 2),
    total_reviews INTEGER DEFAULT 0,
    extracted_weaknesses TEXT[] DEFAULT '{}', -- ARRAY['Warna pudar', 'Stiker mudah sobek', 'Respon lama']
    pricing_notes TEXT,
    ruang_visual_counter_pitch TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TRIGGER update_competitor_matrix_timestamp BEFORE UPDATE ON competitor_matrix FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

-- 8. INDEXES UNTUK KECEPATAN FILTERING DASHBOARD
CREATE INDEX idx_leads_active_verified ON leads(is_active_verified);
CREATE INDEX idx_leads_category ON leads(category);
CREATE INDEX idx_leads_platform ON leads(platform);
CREATE INDEX idx_leads_city ON leads(city);
CREATE INDEX idx_leads_whatsapp ON leads(whatsapp_number);
CREATE INDEX idx_lead_insights_score ON lead_insights(lead_score DESC);
CREATE INDEX idx_crm_outreach_status ON crm_outreach(status);
CREATE INDEX idx_crm_next_follow_up ON crm_outreach(next_follow_up_date);
CREATE INDEX idx_leads_business_name_trgm ON leads USING gin (business_name gin_trgm_ops);

-- 9. TRIGGER FUNGSI: AUTO UPDATE TIMESTAMP
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_target_sources_timestamp BEFORE UPDATE ON target_sources FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER update_leads_timestamp BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER update_lead_insights_timestamp BEFORE UPDATE ON lead_insights FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER update_crm_outreach_timestamp BEFORE UPDATE ON crm_outreach FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
```

---

## 7. Spesifikasi Desain UI/UX Dashboard Lokal (`/market-scraping`)

Dashboard dibangun menggunakan Next.js (App Router) pada sub-halaman aplikasi web RUANG VISUAL. Desain mematuhi secara mutlak *design system* yang telah aktif di Vercel:

### 7.1 Aturan Gaya & Palet Desain CMYK
- **Font Utama**: `Plus Jakarta Sans` dengan styling sans-serif modern yang tegas.
- **Warna Dasar**:
  - `bg-surface`: `#F8FAFC` (kanvas utama yang bersih).
  - `bg-neutral-paper`: `#FFFFFF` (kartu dan kontainer komponen).
  - `text-cmyk-key`: `#0F172A` (warna teks judul dan kontras tinggi).
  - `text-neutral-text-muted`: `#64748B` (warna teks label dan deskripsi sekunder).
  - `border-neutral-border`: `#E2E8F0` (garis tepi tipis berkelas).
- **Aksen Khas RUANG VISUAL**:
  - `cmyk-cyan`: `#00E5FF` (digunakan sebagai aksen status sistem, indikator fokus input, dan garis atas kartu setebal 1px).
  - `cmyk-magenta`: Digunakan untuk penanda prospek prioritas tinggi (skor > 85).
  - `cmyk-yellow`: Digunakan untuk penanda status prospek dalam tahap negosiasi/penawaran.
  - `cmyk-charcoal`: `#1E293B` (warna hover pada tombol aksi utama).
- **Elemen Penanda Proofing**: Setiap kartu utama dilengkapi dengan titik status berukuran 6px (`w-1.5 h-1.5 rounded-full bg-cmyk-cyan`) dan teks penanda mini `Sistem Proofing Terkalibrasi Aktif`.

### 7.2 Anatomi Antarmuka Dashboard

```
+----------------------------------------------------------------------------------------------------+
|  [LOGO RUANG VISUAL]  |  Market Intelligence & Autonomous Prospecting Radar  | Status: Database OK |
+----------------------------------------------------------------------------------------------------+
|  [METRIC BAR: 1,420 Prospek Aktif]  [840 Siap WhatsApp]  [120 Sample Terkirim]  [Rp 42.5M Won Deal] |
+----------------------------------------------------------------------------------------------------+
|  TABS: [ Radar Prospek ]  |  [ Pusat Kampanye Scraping ]  |  [ Matriks Kompetitor ]  |  [ Pengaturan ]|
+----------------------------------------------------------------------------------------------------+
|  FILTER: [Kategori: F&B v] [Platform: All v] [Min Skor: 75 v] [Hanya Ada WA: [x]] [Search Bisnis...] |
+----------------------------------------------------------------------------------------------------+
|  KANBAN PIPELINE VIEW                                                                              |
|  +--------------------+  +--------------------+  +--------------------+  +--------------------+    |
|  | BARU MASUK (124)   |  | SIAP DI-PITCH (45) |  | SAMPEL DIKIRIM(18) |  | DEAL TRANSAKSI(32) |    |
|  +--------------------+  +--------------------+  +--------------------+  +--------------------+    |
|  | - Kopi Kenangan    |  | - Dapur Bunda Nyaman| | - Butik Hijab Ayu  |  | - Resto Ayam Geprek|    |
|  |   Skor: 92 (F&B)   |  |   Skor: 88 (F&B)   |  |   Skor: 95 (Retail)|  |   Skor: 98 (F&B)   |    |
|  |   Kemasan Cup 12oz |  |   Lunchbox Kraft   |  |   Hangtag Gold Foil|  |   10.000 Box Kraft |    |
|  |   [Buka Detail]    |  |   [Kirim WA 1-Klik]|  |   [Resi: JNT90123] |  |   [Siklus: 30 Hari]|    |
|  +--------------------+  +--------------------+  +--------------------+  +--------------------+    |
+----------------------------------------------------------------------------------------------------+
|  DETAIL ACTION DRAWER (Panel Samping Kanan saat Kartu Diklik):                                     |
|  - Profil Lengkap Usaha, Akun Instagram, Lokasi Google Maps                                       |
|  - Status Terakhir Aktif: "Posting 2 hari lalu di Feed"                                            |
|  - Proyeksi Produk: Paper Cup 8oz & 12oz, Cup Sleeve PE Coating, Stiker Segel Anti Air             |
|  - Tombol Aksi: [Kirim WhatsApp via Template F&B]  [Kirim Sample Box]  [Tandai Deal Transaksi]     |
+----------------------------------------------------------------------------------------------------+
```

---

## 8. Playbook Operasional Penjualan & Alur Sample Box Fisik

Sistem tidak hanya menghasilkan data mentah, melainkan memandu tim penjualan mengeksekusi penawaran dengan tingkat keberhasilan tinggi:

### 8.1 Template Penawaran WhatsApp Otomatis (Anti-Broadcast Spam)
Sistem membuat pesan WhatsApp personal berbasis data spesifik entitas bisnis:

#### Template A: Sektor F&B (Fokus: Kemasan Anti Bocor & Ketajaman Warna)
> *"Halo Kak [Nama Owner / Admin] [Nama Bisnis], salam kenal dari tim RUANG VISUAL Printing.*
> 
> *Kami melihat menu [Nama Menu/Produk] di [Platform Instagram/Maps] kakak sangat menarik. Untuk menjaga kepuasan pelanggan saat pesan antar (*takeaway*), RUANG VISUAL menyediakan solusi **Paper Lunch Box Food-Grade** dan **Paper Cup** dengan sistem proofing warna terkalibrasi—sehingga warna logo brand kakak dicetak tajam dan bahan dijamin tahan minyak/panas tanpa bocor.*
> 
> *Apakah kami boleh mengirimkan **Free Sample Box** berisi contoh ketebalan bahan dan hasil cetak fisik kami langsung ke [Alamat Usaha]? Tanpa biaya apa pun, agar kakak bisa memegang dan menguji kualitasnya langsung."*

#### Template B: Sektor Fashion & Retail (Fokus: Kemewahan Hangtag & Packaging)
> *"Halo Kak [Nama Bisnis], salam kenal dari RUANG VISUAL.*
> 
> *Koleksi busana terbaru kakak di feed Instagram terlihat sangat elegan. Untuk menyempurnakan pengalaman unboxing pelanggan, kami menyediakan pembuatan **Hangtag Tebal 400gsm (Laminasi Doff Velvet & Hotprint Emas)** serta **Polymailer Sablon Logo** berkualitas tinggi.*
> 
> *Kami ingin mengirimkan buku katalog bahan fisik ke alamat butik kakak di [Alamat Usaha]. Boleh kami konfirmasikan nama penerima paket sampelnya, Kak?"*

### 8.2 Standard Operating Procedure (SOP) Sample Box Funnel
1. **Identifikasi Prospek Tier-1**: Prospek dengan skor >= 85 dan alamat fisik lengkap dari Google Maps.
2. **Pengemasan Kotak Sampel**:
   - Sampel stiker vinyl doff, glossy, transparan, dan stiker hologram.
   - Contoh paper cup dengan sleeve.
   - Contoh lunch box kraft dan ivory.
   - Sampel kartu ucapan dengan variasi laminasi dan hotprint foil.
   - Surat personalisasi yang dicetak khusus mencantumkan nama brand mereka.
3. **Pengiriman & Pelacakan**: Nomor resi kurir diinput ke tabel `crm_outreach`, status otomatis berubah menjadi `sample_box_dispatched`.
4. **Follow-Up Presisi**: Tiga hari setelah kurir menyatakan paket diterima, sistem menampilkan pengingat di dashboard bagi tim sales untuk menanyakan testimoni uji coba sampel tersebut.

---

## 9. Pembagian Tugas Agen & Batasan Wewenang (Collaboration Rules)

Sesuai aturan operasional multi-agen repositori:

### 9.1 Tugas & Batasan Kilo (Builder & Scraper Specialist)
- **Tanggung Jawab**:
  1. Menulis modul ekstraksi Python di dalam folder `scrapers/` (Instagram, Google Maps, TikTok, Meta Ads).
  2. Mengimplementasikan pustaka Crawlee Python dan TLS client impersonation.
  3. Menulis fungsi regex normalisasi nomor WhatsApp dan fungsi sanitasi alamat.
  4. Menulis kalkulator skor prospek (`lead_scoring.py`) sesuai formula Bab 5.
  5. Menulis unit test mandiri pada folder `tests/` dan menguji dengan flag `--dry-run`.
- **Batasan Mutlak Kilo**:
  - Dilarang keras mengubah arsitektur utama dashboard Next.js tanpa persetujuan Antigravity.
  - Dilarang menjalankan skrip produksi yang mengubah database tanpa mode dry-run.
  - Wajib memeriksa sintaks sebelum serah terima: `python3 -m py_compile <file>`.

### 9.2 Tugas & Batasan Antigravity (Architect, Auditor & Integrator)
- **Tanggung Jawab**:
  1. Menjaga integritas PRD, database Supabase, dan aturan bebas emoji.
  2. Mengaudit setiap baris kode yang ditulis Kilo (keamanan, efisiensi memori, ketiadaan emoji).
  3. Mengembangkan frontend dashboard lokal Next.js dan API routing Supabase.
  4. Menghubungkan webhook Apify Cloud ke database Supabase.
  5. Melakukan pengujian end-to-end dan mengelola Git commit.

---

## 10. Roadmap Implementasi 4 Tahap (Milestones)

- **Milestone 1: Database Setup & Local Next.js Dashboard Foundation**
  - Eksekusi skrip DDL Supabase lengkap (tabel, enum, index, trigger).
  - Pembangunan kerangka antarmuka lokal Next.js di rute `/market-scraping` dengan styling CMYK RUANG VISUAL.
  - Verifikasi konektivitas data API Supabase.
- **Milestone 2: Mesin Ekstraksi Inti (Instagram & Google Maps Engine)**
  - Implementasi Follower/Following Spider untuk pengikut akun bazar kuliner dan kompetitor.
  - Implementasi Place Scout Google Maps untuk entitas usaha baru dan alamat fisik.
  - Pengujian filter keaktifan post < 30 hari dan normalisasi nomor WhatsApp.
- **Milestone 3: CRM Kanban, 1-Click WhatsApp & Sample Box Tracking**
  - Penyambungan tabel Supabase ke komponen Kanban Board interaktif.
  - Generator tautan chat WhatsApp otomatis sesuai sektor bisnis.
  - Modul pencatatan resi pengiriman *Sample Box* fisik.
- **Milestone 4: Ekspansi Multi-Platform & Entity Matcher**
  - Integrasi penjelajah Meta Ads Library dan TikTok Shop seller scraper.
  - Implementasi algoritma pencocokan nama merchant Food Delivery ke Instagram dan Maps.
  - Peluncuran sistem penuh untuk tim operasional pemasaran RUANG VISUAL.
