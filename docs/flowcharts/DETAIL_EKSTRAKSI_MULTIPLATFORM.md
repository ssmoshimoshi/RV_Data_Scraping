# Spesifikasi Rinci Ekstraksi Data Multi-Platform RUANG VISUAL

Dokumen ini melengkapi diagram grafis beresolusi tinggi pada file:
[flowchart_multiplatform_scraping_detailed.png](file:///Users/muhammadfanani/Documents/2026%20COMMISSION/RUANG%20VISUAL/DATA%20CALON%20CUSTOMER/docs/flowcharts/flowchart_multiplatform_scraping_detailed.png)

Dokumen ini membedah setiap titik data (*data points*), parameter logika, dan metode ekstraksi untuk setiap platform yang disasar.

---

## Diagram Arsitektur Alur Sistem Lengkap (Mermaid Diagram)

```mermaid
flowchart TD
    subgraph MultiVector["1. Multi-Vector Data Ingestion"]
        GMAPS["Google Maps Compass\n(Place ID, Alamat, Rating, Reviews)"]
        FOOD["Food Delivery Apps\n(GoFood, GrabFood, ShopeeFood)"]
        IG["Instagram Spider & Profile\n(Tombol WA, Followers, 5 Postingan)"]
        TIKTOK["TikTok Shop & Creators\n(Etalase, Hashtag Kemasan)"]
        ADS["Meta Ads Library\n(Iklan Berbayar Aktif, CTA WA/Web)"]
    end

    subgraph CleaningLayer["2. Data Normalization & Cleaning"]
        NORM_WA["Normalisasi WhatsApp\n(Baku: 628xxxxxxxxxx)"]
        NORM_ADDR["Normalisasi Alamat & Wilayah\n(Kecamatan, Kota, Geocoding)"]
        DATASET_RUN["Extract Dataset ID\n(Kompatibel Pydantic Run modern)"]
    end

    subgraph EntityMatcherLayer["3. Cross-Platform Entity Matcher"]
        EXACT_PHONE{"Pencocokan Nomor WA"}
        FUZZY_NAME{"Fuzzy Matching Nama\n(Jaro-Winkler >= 0.85)"}
        GEO_DIST{"Verifikasi Radius Geo\n(< 150 meter)"}
        UNIFIED_LEAD["Unified Customer Dossier Profile"]
    end

    subgraph IntelligenceEngines["4. RUANG VISUAL Intelligence Engines"]
        PILLARS_4["Universal 4-Pillars Scoring\n- Legitimasi Fisik (25)\n- Kecepatan Komersial (25)\n- Turnover Kemasan (30)\n- Anggaran Iklan (20)"]
        PAIN_POINTS["Packaging Pain Points Engine\n(Keyword Matcher: bocor, rembes, robek)\n-> Sudut Penawaran RUANG VISUAL"]
        COMM_EST["Packaging Commercial Estimator\n- Tier Prioritas 1/2/3\n- Konsumsi Unit Bulanan\n- Estimasi Omzet & Restock"]
    end

    subgraph LocalDashboard["5. Local Dossier Dashboard (localhost:3000/market-scraping)"]
        TABLE_DOSSIER["Tabel Intelijen Pasar\n(Anchor Maps, Tier Komersial, Skor)"]
        DRAWER_MODAL["Detail Drawer Modal CMYK\n(Breakdown 4 Pilar, Pain Points, Commercials)"]
        CONTENT_INSPECTOR["Deep Content Inspector\n(Top 5 Posts, Engagement Rate, Velocity)"]
        ONE_CLICK_WA["1-Click WhatsApp Pitch Generator\n(Draft Pesan Khusus Sektor Industri)"]
    end

    subgraph CloudStorage["6. Persistent Storage Layer"]
        RAW_JSON["Local Raw Storage\n(data/raw/gmaps_places_*.json)"]
        SUPABASE_DB["Supabase PostgreSQL 15+\n(leads, lead_insights, crm_outreach)"]
    end

    GMAPS --> NORM_WA & NORM_ADDR & DATASET_RUN
    FOOD --> NORM_WA & NORM_ADDR & DATASET_RUN
    IG --> NORM_WA & DATASET_RUN
    TIKTOK --> NORM_WA
    ADS --> NORM_WA & DATASET_RUN

    NORM_WA & NORM_ADDR & DATASET_RUN --> EXACT_PHONE
    EXACT_PHONE -- Cocok --> UNIFIED_LEAD
    EXACT_PHONE -- Tidak Cocok --> FUZZY_NAME
    FUZZY_NAME -- Mirip --> GEO_DIST
    GEO_DIST -- Dekat --> UNIFIED_LEAD
    FUZZY_NAME -- Entitas Baru --> UNIFIED_LEAD

    UNIFIED_LEAD --> PILLARS_4
    UNIFIED_LEAD --> PAIN_POINTS
    UNIFIED_LEAD --> COMM_EST

    PILLARS_4 & PAIN_POINTS & COMM_EST --> RAW_JSON
    RAW_JSON --> TABLE_DOSSIER
    TABLE_DOSSIER --> DRAWER_MODAL & CONTENT_INSPECTOR & ONE_CLICK_WA
    UNIFIED_LEAD -. Sinkronisasi Database Cloud .-> SUPABASE_DB
```

---

## 1. Lane 1: Ekstraksi Instagram (The Relationship & Activity Layer)

Instagram adalah kanal primer penentu keaktifan entitas bisnis. Ekstraksi terbagi menjadi 6 tahapan berurutan:

### A. Follower & Following Graph
- **Target Sumber**: Akun kurasi event kuliner lokal (contoh: bazar kampus, festival kuliner kota), asosiasi UMKM daerah, dan 3-5 akun percetakan kompetitor utama.
- **Data yang Diambil**:
  - `target_username`: Username akun yang di-follow / follower.
  - `profile_url`: URL langsung ke akun profil.
  - `relationship_type`: Penanda apakah akun tersebut merupakan pengikut kompetitor atau peserta event.

### B. Bio Text Parsing
- **Data yang Diambil**: Teks deskripsi profil lengkap.
- **Logika Ekstraksi**:
  - Pemindaian kata kunci operasional: "Order", "Pemesanan", "Buka", "Menu", "Katalog", "Pricelist", "Delivery".
  - Pendeteksian link eksternal: Linktree, biolinky, bit.ly, atau domain mandiri.

### C. Direct WhatsApp & Call Button
- **Mekanisme**: Mengakses metadata tombol kontak bisnis resmi Instagram (Action Buttons: Call, Email, WhatsApp Business).
- **Keunggulan**: Mengambil nomor valid yang didaftarkan langsung oleh pemilik bisnis ke sistem Meta, tanpa bergantung pada penulisan nomor yang acak di teks bio.

### D. Recent Posts Timestamps (< 30 Hari)
- **Mekanisme**: Membaca 3-5 unggahan feed/reels paling mutakhir.
- **Data yang Diambil**:
  - `post_timestamp`: Tanggal dan jam unggahan terakhir.
  - `days_since_last_post`: Selisih hari dari saat ini ke unggahan terakhir.
- **Aturan Ambang Batas**:
  - Jika `days_since_last_post` <= 30 hari: Lolos verifikasi (`is_active_verified = true`).
  - Jika `days_since_last_post` > 30 hari: Akun dianggap vakum/tutup, status di-drop atau ditandai *Inactive*.

### E. Comments with Buyer Intent
- **Mekanisme**: Memindai komentar pada postingan promosi akun kompetitor atau event.
- **Kata Kunci Pemicu**: "Bisa custom?", "Berapa harganya kak?", "Minimal order berapa?", "Kirim ke mana aja?".
- **Output**: Profil pengguna yang menanyakan harga kemasan langsung diprioritaskan sebagai prospek panas.

### F. Geotags Lokasi
- **Data yang Diambil**: Label lokasi pada unggahan (nama mall, pasar sentral, sentra kuliner, nama jalan).
- **Pemanfaatan**: Menentukan zona area workshop/toko untuk memetakan radius logistik pengiriman dari workshop RUANG VISUAL.

---

## 2. Lane 2: Ekstraksi Google Maps (The Physical & Location Layer)

Google Maps memberikan validitas keberadaan toko fisik dan celah kualitas kompetitor.

### A. Business Name & Category
- **Target Kategori**: Kafe, Coffee Shop, Rumah Makan, Bakery, Klinik Kecantikan, Butik Baju, Kantor Notaris, Percetakan.
- **Data yang Diambil**: Nama resmi bisnis, kategori primer, dan kategori sekunder.

### B. Full Physical Address & Coordinates
- **Data yang Diambil**:
  - `address_full`: Alamat fisik jalan, kelurahan, kecamatan, kota, kode pos.
  - `latitude` & `longitude`: Titik koordinat peta presisi.
- **Pemanfaatan Strategis**: Alamat lengkap digunakan untuk mengirimkan paket contoh fisik cetak (*sample box*) langsung ke meja pemilik bisnis.

### C. Phone Number & Website
- **Data yang Diambil**: Nomor telepon tetap kantor atau nomor handphone seluler yang tertera di listing Google Bisnisku.

### D. Review Score & Count (Saringan Tempat Baru)
- **Logika Sinyal Bisnis Baru**:
  - Bisnis dengan ulasan kurang dari 15 ulasan dan status "Buka Baru" / "Opening Soon" diproyeksikan membutuhkan paket branding toko baru (Neon box, spanduk, banner, signage kaca).

### E. Competitor Negative Review Mining (Celah Kompetitor)
- **Mekanisme**: Mengikis seluruh ulasan dengan bintang 1 hingga 3 pada listing percetakan kompetitor.
- **Analisis Sentimen Keluhan**:
  - Keluhan: "Warna tidak sesuai desain", "Bahan stiker tipis dan luntur", "Pengerjaan lama tidak tepat waktu".
  - **Output**: Disimpan di tabel sebagai konteks pitching agar tim sales RUANG VISUAL dapat menawarkan keunggulan mesin proofing terkalibrasi.

---

## 3. Lane 3: Ekstraksi TikTok (The Live Commerce & Packaging Volume Layer)

TikTok menargetkan seller yang memiliki volume pengiriman barang harian yang masif.

### A. Creator Profile & Showcase/Bio Link
- **Data yang Diambil**: Handle akun, nama brand, link etalase TikTok Shop, dan link kontak WhatsApp di bio.

### B. Video Captions & Hashtag Trends
- **Hashtag Target**: `#kulinermakassar`, `#hamperslebaran`, `#kemasanmakanan`, `#unboxingpaket`, `#umkmlokal`.
- **Pemanfaatan**: Mengetahui produk apa yang sedang viral di pasar lokal yang membutuhkan kemasan massal baru.

### C. Live Commerce Seller Badges
- **Sinyal Kebutuhan**: Akun yang memiliki badge seller aktif atau rutin melakukan live streaming belanja.
- **Proyeksi Kebutuhan Cetak**: Membutuhkan ribuan lembar stiker resi thermal, stiker logo pengiriman, kartu ucapan terima kasih (*thank you card*), dan box kardus die-cut custom.

---

## 4. Lane 4: Ekstraksi Meta Ads & Marketplace (The Commercial Budget Layer)

Meta Ads membidik brand yang terbukti memiliki alokasi anggaran promosi berbayar.

### A. Active Sponsored Ad Text
- **Sumber**: Meta Ad Library publik.
- **Data yang Diambil**:
  - Teks promosi kampanye iklan.
  - Tanggal mulai penayangan iklan.
  - Format iklan (gambar, video, carousel).

### B. Call-to-Action (CTA) Links
- **Data yang Diambil**: URL tujuan iklan (Landing page, nomor WhatsApp langsung, atau katalog website).
- **Skor Prioritas**: Brand yang sedang beriklan aktif otomatis mendapatkan skor minimal 85/100 karena memiliki anggaran belanja promosi aktif.

### C. Unbranded Marketplace Listings (Facebook Marketplace)
- **Metode**: Pencarian produk makanan, kue kering, atau fashion buatan rumahan di Facebook Marketplace.
- **Sinyal Peluang**: Penjual yang menggunakan kemasan toples atau plastik polos tanpa stiker merek ditandai sebagai target penawaran paket stiker UMKM pemula.

### D. Local UMKM Groups
- **Sumber**: Grup komunitas pedagang dan pengusaha daerah di Facebook.
- **Data yang Diambil**: Postingan pemilik usaha yang mencari rekomendasi vendor kemasan atau percetakan.

---

## 5. Lane 5: Sinyal Food Delivery Apps (The Packaging Consumption Layer)

ShopeeFood, GoFood, dan GrabFood mendeteksi kebutuhan kemasan makanan harian.

### A. Merchant Directory Scraping
- **Data yang Diambil**: Nama restoran, nama cabang, kategori makanan, dan jam operasional.

### B. Food Photos for Packaging Inspection
- **Metode**: Memindai foto menu yang diunggah oleh merchant.
- **Analisis Kebutuhan**:
  - Resto yang masih memakai box styrofoam atau kantong kresek polos ditargetkan untuk peningkatan ke *paper lunch box* ramah lingkungan dan *paper bag* berlogo.

### C. Cross-Platform Entity Matching
- **Kritikal**: Karena aplikasi food delivery menyamarkan nomor kontak penjual (*masked number*), sistem menjalankan pencocokan otomatis:
  - Mengambil `Nama Restoran` + `Nama Cabang/Kota`.
  - Mencari kecocokan profil di Instagram dan Google Maps secara otomatis.
  - Mengambil nomor WhatsApp dan alamat fisik dari hasil pencocokan tersebut.

---

## 6. Verification & Filter Engine (Saringan Anti-Sampah)

Seluruh data mentah dari Lane 1 sampai 5 wajib melewati gerbang verifikasi sebelum masuk database:

1. **Recency Check**:
   - Jika data berasal dari media sosial, postingan terakhir wajib < 30 hari. Jika tidak, data diabaikan.
2. **WhatsApp Normalization**:
   - Menghapus karakter khusus (spasi, tanda plus, strip, kurung).
   - Mengubah awalan `08` atau `+628` menjadi format baku internasional `628xxxxxxxxxx`.
   - Memvalidasi panjang nomor (antara 10 hingga 14 digit).
3. **Lead Scoring Engine**:
   Formula kalkulasi skor prospek (bobot per komponen dan aturan cap maksimum 100) didefinisikan secara tunggal di:
   `PRD_RUANG_VISUAL_MARKET_INTELLIGENCE.md` — Bab 5.2 (Single Source of Truth).
   Kilo wajib mengacu ke dokumen tersebut, bukan mendefinisikan ulang di sini.

---

## 7. Supabase Database & CRM Execution

Data yang lolos verifikasi langsung disimpan ke tabel relasional Supabase (`leads`, `lead_insights`, `crm_outreach`) dan langsung ditampilkan pada dashboard lokal:
- **Kanban Board**: Menggeser status dari *Prospek Baru* -> *Siap Dihubungi* -> *Terkirim Pesan* -> *Sampel Terkirim* -> *Deal*.
- **1-Click WhatsApp Direct Chat**: Membuka WhatsApp Web / Desktop dengan draft pesan penawaran otomatis yang menyebutkan nama bisnis dan produk cetak yang relevan.
- **Physical Sample Kit Delivery**: Mencetak label pengiriman sampel paket bahan cetak ke alamat fisik toko yang didapat dari Google Maps.
