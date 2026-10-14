# PRD: RUANG VISUAL — Market Intelligence & Lead Generation Pipeline
### Versi 2.0 — Dokumen Rujukan Utama

**Entity:** PT Estetika Ruang Visual / RUANG VISUAL  
**Lokasi:** Makassar, Sulawesi Selatan  
**Industri:** Percetakan (B2B & Retail)  
**Tanggal:** 14 Oktober 2026  
**Status:** [SELESAI] APPROVED — Siap Eksekusi

> [!IMPORTANT]
> **INSTRUKSI UNTUK AGENT:** Dokumen ini adalah **single source of truth** untuk seluruh project.
> Setiap kali menerima perintah terkait scraping, lead generation, atau competitor analysis,
> **BACA DOKUMEN INI TERLEBIH DAHULU** sebelum mengambil tindakan apapun.

---

## DAFTAR ISI

1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Konteks Bisnis](#2-konteks-bisnis)
3. [System Constraints](#3-system-constraints)
4. [Arsitektur Sistem](#4-arsitektur-sistem)
5. [Tech Stack](#5-tech-stack)
6. [Module A — Infrastructure & MCP (SELESAI)](#6-module-a--infrastructure--mcp-selesai)
7. [Module B — Google Maps Scraper](#7-module-b--google-maps-scraper)
8. [Module C — Instagram Scraper](#8-module-c--instagram-scraper)
9. [Module D — TikTok Scraper](#9-module-d--tiktok-scraper)
10. [Module E — Lead Scoring Engine](#10-module-e--lead-scoring-engine)
11. [Module F — Competitor Matrix](#11-module-f--competitor-matrix)
12. [Data Schema (Google Sheets)](#12-data-schema-google-sheets)
13. [Struktur Direktori](#13-struktur-direktori)
14. [Fase Implementasi](#14-fase-implementasi)
15. [Risk Register](#15-risk-register)
16. [Success Metrics](#16-success-metrics)
17. [Keputusan Arsitektur (ADR)](#17-keputusan-arsitektur-adr)
18. [Referensi & Repo Open-Source](#18-referensi--repo-open-source)

---

## 1. Ringkasan Eksekutif

### Apa yang Dibangun
Sistem scraping multi-platform yang mengekstrak data **calon customer** dan **kompetitor** bisnis percetakan di wilayah Makassar. Data dikumpulkan dari Google Maps, Instagram, dan TikTok, kemudian disimpan dan di-scoring di Google Sheets.

### Tujuan Utama
1. **Lead Generation:** Menemukan bisnis baru di Makassar (F&B, retail, EO, instansi) yang berpotensi membutuhkan jasa cetak (kartu nama, brosur, banner, packaging, stiker)
2. **Competitor Intelligence:** Memetakan kelemahan operasional dan pricing gap kompetitor percetakan di Makassar
3. **Market Signal:** Mendeteksi tren desain dan demand shift dari social media

### Batasan Scope
- **DALAM SCOPE:** Google Maps, Instagram, TikTok, Google Sheets
- **DI LUAR SCOPE (untuk saat ini):** Shopee, Tokopedia, Facebook, LPSE, Web umum
- **ALASAN:** Shopee/Tokopedia butuh proxy berbayar; Facebook terlalu agresif anti-bot; LPSE dan web umum bisa ditambah nanti tanpa perubahan arsitektur

---

## 2. Konteks Bisnis

### Profil Perusahaan
- **Nama:** RUANG VISUAL (PT Estetika Ruang Visual)
- **Layanan:** Percetakan B2B & retail — kartu nama, brosur, banner, stiker die-cut, packaging, merchandise (tumbler, mug)
- **Wilayah Target:** Makassar dan sekitarnya
- **Segmen Customer Ideal:**
  - F&B baru buka (butuh menu, banner, packaging)
  - Event Organizer (butuh banner, backdrop, undangan)
  - Retail/UMKM baru (butuh kartu nama, brosur, stiker produk)
  - Instansi/kantor (butuh cetak dokumen, ID card, signage)

### Kompetitor Utama (Contoh — akan divalidasi saat scraping)
Percetakan di Makassar yang aktif di Google Maps dan social media. Nama spesifik akan di-extract oleh Module B & F.

### Pain Point yang Diselesaikan
1. Tidak ada cara sistematis menemukan bisnis baru yang butuh jasa cetak
2. Tidak tahu kelemahan kompetitor untuk dijadikan selling point
3. Informasi pasar hanya dari mulut ke mulut, bukan data

---

## 3. System Constraints

> [!CAUTION]
> **Constraint berikut HARUS dipatuhi di setiap module.** Jangan mengusulkan solusi yang melanggar constraint ini tanpa persetujuan eksplisit dari owner.

### Hardware
| Parameter | Nilai | Implikasi |
|-----------|-------|-----------|
| **OS** | macOS Apple Silicon | Native Python support, Playwright support |
| **RAM** | **8GB** | Maks 1 headless browser pada satu waktu. Tidak bisa jalankan LLM lokal |
| **Development IDE** | Google Antigravity IDE | MCP via stdio |

### Budget
| Parameter | Nilai | Implikasi |
|-----------|-------|-----------|
| **Budget bulanan** | **Rp 0 (gratis)** | Tidak pakai proxy berbayar, tidak pakai LLM API berbayar |
| **Google Cloud** | Service Account (sudah ada) | Google Sheets API gratis dalam quota |

### Operasional
| Parameter | Nilai | Implikasi |
|-----------|-------|-----------|
| **Frekuensi scraping** | **1x/minggu atau 1x/bulan** | Risiko ban sangat rendah |
| **Operator** | Owner (manual trigger) | Bukan fully automated, bukan cron job |
| **Skala target** | 100-500 leads + 10-20 kompetitor/bulan | Volume sedang |

### Larangan Teknis (Hard Rules)
1. [DILARANG] **JANGAN** gunakan LLM API berbayar (OpenAI, Anthropic, dll)
2. [DILARANG] **JANGAN** gunakan Ollama/model lokal (RAM tidak cukup)
3. [DILARANG] **JANGAN** jalankan lebih dari 1 headless browser bersamaan
4. [DILARANG] **JANGAN** install Docker containers berat (RAM constraint)
5. [DILARANG] **JANGAN** gunakan proxy berbayar
6. [SELESAI] **BOLEH** gunakan Gemini API jika ada free tier yang cukup
7. [SELESAI] **BOLEH** upgrade constraint di masa depan dengan persetujuan owner

---

## 4. Arsitektur Sistem

### Diagram Arsitektur

```
┌─────────────────────────────────────────────────────────────┐
│                    OPERATOR (Owner)                          │
│              Manual trigger via terminal/IDE                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR LAYER                           │
│                                                             │
│  ┌─────────────────┐    ┌───────────────────────────────┐   │
│  │  Hermes Agent   │◄──►│  MCP Server (Google Sheets)   │   │
│  │  (Antigravity)  │    │  hermes-mcp-server/server.py  │   │
│  └────────┬────────┘    └───────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │  Runner Script  │ ← python run_pipeline.py [module]      │
│  │  (CLI trigger)  │                                        │
│  └────────┬────────┘                                        │
└───────────┼─────────────────────────────────────────────────┘
            │
    ┌───────┼──────────┬──────────────────┐
    ▼       ▼          ▼                  ▼
┌────────┐ ┌────────┐ ┌────────┐  ┌──────────────┐
│Mod B   │ │Mod C   │ │Mod D   │  │  Mod E & F   │
│G.Maps  │ │Insta   │ │TikTok  │  │  Scoring &   │
│Fetcher │ │Stealth │ │Stealth │  │  Analysis    │
└───┬────┘ └───┬────┘ └───┬────┘  └──────┬───────┘
    │          │          │               │
    └──────────┼──────────┘               │
               ▼                          │
    ┌──────────────────┐                  │
    │  Scrapling Core  │                  │
    │  (Parser +       │                  │
    │   Adaptive CSS)  │                  │
    └────────┬─────────┘                  │
             │                            │
             ▼                            ▼
    ┌──────────────────────────────────────────┐
    │         GOOGLE SHEETS (via MCP)          │
    │                                          │
    │  ┌──────────────┐  ┌──────────────────┐  │
    │  │Radar Prospek │  │Matriks Kompetitor│  │
    │  └──────────────┘  └──────────────────┘  │
    │  ┌──────────────┐  ┌──────────────────┐  │
    │  │Market Signal │  │  Scrape Log      │  │
    │  └──────────────┘  └──────────────────┘  │
    └──────────────────────────────────────────┘
```

### Prinsip Arsitektur
1. **Modular:** Setiap platform = 1 module Python terpisah. Bisa dijalankan sendiri-sendiri.
2. **Sequential:** Hanya 1 module jalan pada satu waktu (constraint RAM 8GB).
3. **Adaptive:** Pakai Scrapling adaptive selectors agar tahan perubahan layout.
4. **Stateless Scraper:** Setiap run = fresh state. Tidak tergantung run sebelumnya.
5. **Google Sheets as Database:** Semua output ke Sheets via MCP server yang sudah ada.

---

## 5. Tech Stack

### Core Framework
| Komponen | Tool | Versi | Alasan Pemilihan |
|----------|------|-------|------------------|
| **Scraping Framework** | [Scrapling](https://github.com/D4Vinci/Scrapling) | Latest |  bintang87.5k stars, adaptive selectors, stealth bypass, MCP built-in, Python native, ringan |
| **HTTP Fetching** | Scrapling `Fetcher` | — | Untuk Google Maps (HTTP tanpa browser) |
| **Stealth Browsing** | Scrapling `StealthyFetcher` | — | Untuk Instagram & TikTok (bypass anti-bot) |
| **HTML Parsing** | Scrapling Parser | — | Adaptive CSS/XPath, survive layout changes |

### Infrastructure (SUDAH ADA)
| Komponen | Tool | Status |
|----------|------|--------|
| **MCP Server** | Python MCP SDK (stdio) | [SELESAI] Sudah dibangun |
| **Database** | Google Sheets API v4 | [SELESAI] Sudah terkoneksi |
| **Auth** | GCP Service Account | [SELESAI] Sudah dikonfigurasi |
| **Env Management** | python-dotenv | [SELESAI] Sudah ada |

### Dependencies Baru yang Dibutuhkan
```
# Ditambahkan ke requirements.txt
scrapling[fetchers]          # Core scraping + browser fetchers
```

Setelah install, jalankan:
```bash
scrapling install            # Download browser dependencies
```

---

## 6. Module A — Infrastructure & MCP (SELESAI)

> **Status: [SELESAI] COMPLETE**

### Yang Sudah Ada
- `hermes-mcp-server/server.py` — MCP server via stdio transport
- `hermes-mcp-server/init_pipeline_sheets.py` — Script inisialisasi Google Sheets
- `hermes-mcp-server/.env.example` — Template konfigurasi
- `hermes-mcp-server/credentials/` — Folder untuk service account JSON

### MCP Tools yang Tersedia
| Tool | Fungsi |
|------|--------|
| `create_sheet` | Membuat worksheet/tab baru |
| `read_sheet` | Membaca data dari worksheet |
| `append_row` | Menambahkan baris baru |
| `update_cell` | Update satu sel spesifik |

### Google Sheets yang Sudah Diinisialisasi
1. **Radar Prospek** — kolom: Entitas Bisnis, Kategori Segmen, Trigger Event, Proyeksi Kebutuhan, Skor Prospek, Status Akuisisi
2. **Matriks Kompetitor** — kolom: Nama Kompetitor, Fokus Layanan Utama, Celah Kualitas, Celah SOP/Admin, Estimasi Kapasitas, Estetika Visual

---

## 7. Module B — Google Maps Scraper

> **Status: [BELUM DIBANGUN] BELUM DIBANGUN**  
> **Prioritas: #1 (paling valuable, paling mudah)**  
> **Estimasi Build Time: 2-4 jam**

### Objektif
Mengekstrak data bisnis dari Google Maps untuk dua tujuan:
1. **Lead Generation:** Menemukan bisnis baru yang potensial butuh jasa cetak
2. **Competitor Mapping:** Menemukan semua percetakan di Makassar

### Teknis Implementasi
- **Fetcher:** `Scrapling.Fetcher` (HTTP-only, TANPA browser — hemat RAM)
- **Alternatif cadangan:** `omkarcloud/google-maps-scraper` jika Fetcher tidak cukup
- **Anti-ban strategy:** Sequential request, delay 3-5 detik, 1x/minggu

### Search Queries — Lead Generation

```python
LEAD_QUERIES = [
    # F&B (prioritas tinggi — sering butuh menu, banner, packaging)
    "cafe baru Makassar",
    "restoran baru Makassar",
    "kedai kopi Makassar",
    "catering Makassar",
    
    # Retail & UMKM
    "toko baru Makassar",
    "UMKM Makassar",
    "oleh-oleh khas Makassar",
    
    # Event & Jasa
    "event organizer Makassar",
    "wedding organizer Makassar",
    "jasa fotografi Makassar",
    
    # Instansi & Kantor
    "kantor baru Makassar",
    "coworking space Makassar",
    "klinik baru Makassar",
]
```

### Search Queries — Competitor Mapping

```python
COMPETITOR_QUERIES = [
    "percetakan Makassar",
    "digital printing Makassar",
    "cetak banner Makassar",
    "cetak stiker Makassar",
    "cetak kartu nama Makassar",
    "percetakan offset Makassar",
    "printing Makassar",
]
```

### Data yang Diekstrak per Listing

```python
GMAPS_SCHEMA = {
    "nama_bisnis": str,          # Nama entitas
    "kategori": str,             # Jenis bisnis (restaurant, retail, dll)
    "alamat": str,               # Alamat lengkap
    "telepon": str,              # Nomor telepon (lead contact)
    "website": str,              # URL website jika ada
    "rating": float,             # Rating Google (1-5)
    "jumlah_review": int,        # Total review
    "jam_operasional": str,      # Jam buka
    "url_gmaps": str,            # Direct link ke Google Maps
    "tanggal_review_pertama": str,  # Estimasi kapan buka (dari review)
    "scrape_date": str,          # Tanggal scraping
    "source": "google_maps",     # Sumber data
}
```

### Filter Logic
- **Bisnis baru:** Review pertama < 6 bulan yang lalu
- **Area:** Hanya Makassar dan sekitarnya
- **Exclude:** Bisnis yang sudah jadi klien (akan dicek manual)

### Output
- Leads → append ke sheet **"Radar Prospek"**
- Competitors → append ke sheet **"Matriks Kompetitor"**

---

## 8. Module C — Instagram Scraper

> **Status: [BELUM DIBANGUN] BELUM DIBANGUN**  
> **Prioritas: #2**  
> **Estimasi Build Time: 3-5 jam**

### Objektif
1. **Competitor Monitoring:** Pantau akun IG kompetitor percetakan — lihat portfolio, harga, engagement
2. **Lead Discovery:** Temukan bisnis baru di Makassar yang aktif promosi via IG
3. **Hashtag Monitoring:** Pantau hashtag terkait percetakan Makassar

### Teknis Implementasi
- **Fetcher:** `Scrapling.StealthyFetcher` (headless browser + stealth mode)
- **Anti-ban strategy:** 
  - Maks **15-20 halaman per session**
  - Delay **5-10 detik** antar request
  - Frekuensi: **1x/minggu MAKS**
  - JANGAN login — scrape data publik saja
  - Gunakan `network_idle=True` untuk tunggu page load penuh

### Target Hashtags

```python
IG_HASHTAGS = [
    "percetakanmakassar",
    "cetakmakassar",
    "printingmakassar",
    "stikermakasar",
    "bannermakassar",
    "cetakmurah",
    "digitalprinting",
    "percetakan",
]
```

### Target Akun Kompetitor
Akan diisi dari hasil Module B (Google Maps) — ambil akun IG dari website/profil GMaps.

### Data yang Diekstrak

```python
IG_SCHEMA = {
    # Dari profil bisnis
    "username": str,
    "nama_display": str,
    "bio": str,
    "jumlah_followers": int,
    "jumlah_following": int,
    "jumlah_posts": int,
    "website_link": str,
    "kategori_bisnis": str,
    "kontak": str,              # Telepon/email dari bio
    
    # Dari posting (opsional, hanya 5-10 post terakhir)
    "recent_posts": [{
        "caption_snippet": str,  # 200 char pertama
        "likes": int,
        "comments": int,
        "date": str,
        "is_pricing_post": bool, # Apakah menyebut harga
    }],
    
    "scrape_date": str,
    "source": "instagram",
}
```

### Rate Limiting Rules

> [!WARNING]
> **WAJIB DIPATUHI untuk menghindari ban Instagram:**
> - Maks 15 profil per session
> - Delay minimum 5 detik antar page load
> - JANGAN login, JANGAN pakai cookie
> - Jika mendapat HTTP 429 atau redirect ke login page → STOP SEGERA
> - Tunggu minimal 24 jam sebelum retry

---

## 9. Module D — TikTok Scraper

> **Status: [BELUM DIBANGUN] BELUM DIBANGUN**  
> **Prioritas: #3**  
> **Estimasi Build Time: 3-5 jam**

### Objektif
1. **Trend Detection:** Temukan video viral terkait percetakan/printing
2. **Competitor Activity:** Pantau kompetitor yang aktif di TikTok
3. **Lead Discovery:** Bisnis Makassar yang promosi via TikTok

### Teknis Implementasi
- **Fetcher:** `Scrapling.StealthyFetcher` (headless, stealth)
- **Anti-ban strategy:**
  - Maks **10-15 halaman per session**
  - Delay **5-10 detik** antar request
  - TikTok web lebih lenient dari IG, tapi tetap hati-hati

### Search Keywords

```python
TIKTOK_KEYWORDS = [
    "percetakan Makassar",
    "cetak stiker",
    "digital printing",
    "packaging custom",
    "cetak banner",
    "printing murah",
    "usaha percetakan",
]
```

### Data yang Diekstrak

```python
TIKTOK_SCHEMA = {
    "username": str,
    "display_name": str,
    "video_title": str,
    "video_url": str,
    "views": int,
    "likes": int,
    "comments": int,
    "shares": int,
    "hashtags": [str],
    "is_competitor": bool,      # Apakah akun percetakan
    "is_potential_lead": bool,  # Apakah bisnis yang butuh cetak
    "lokasi": str,              # Jika terdeteksi Makassar
    "scrape_date": str,
    "source": "tiktok",
}
```

---

## 10. Module E — Lead Scoring Engine

> **Status: [BELUM DIBANGUN] BELUM DIBANGUN**  
> **Prioritas: Dibangun bersamaan Module B**  
> **Estimasi Build Time: 1-2 jam**

### Objektif
Memberikan skor 1-10 pada setiap lead berdasarkan kriteria yang terukur, sehingga owner bisa prioritaskan follow-up.

### Scoring Rules

```python
SCORING_RULES = {
    # Faktor Positif (tambah skor)
    "ada_nomor_telepon":        +2,  # Bisa langsung dihubungi
    "ada_website":              +1,  # Bisnis serius
    "ada_akun_instagram":       +1,  # Aktif di social media
    "kategori_fnb":             +3,  # F&B = butuh menu, banner, packaging
    "kategori_eo":              +3,  # EO = butuh banner, backdrop
    "kategori_retail":          +2,  # Retail = butuh branding
    "kategori_instansi":        +2,  # Instansi = butuh cetak dokumen
    "bisnis_baru_6bulan":       +2,  # Baru buka = butuh branding awal
    "bisnis_baru_3bulan":       +3,  # Sangat baru = sangat butuh
    "rating_dibawah_4":         +1,  # Mungkin butuh upgrade branding
    "lokasi_makassar_kota":     +1,  # Dekat = mudah dijangkau
    
    # Faktor Negatif (kurangi skor)
    "sudah_punya_branding_kuat": -2, # Mungkin sudah punya percetakan langganan
    "franchise_nasional":        -3, # Branding dari pusat
}
```

### Skor Interpretasi
| Skor | Label | Aksi |
|------|-------|------|
| 8-10 |  HOT | Follow up dalam 24 jam |
| 5-7 |  WARM | Follow up dalam 1 minggu |
| 3-4 |  COOL | Masukkan ke nurturing list |
| 1-2 |  COLD | Arsipkan, cek ulang 3 bulan |

### Implementasi
- Rule-based logic di Python (BUKAN LLM)
- Skor ditulis ke kolom **"Skor Prospek"** di sheet Radar Prospek
- Sortir otomatis dari skor tertinggi

---

## 11. Module F — Competitor Matrix

> **Status: [BELUM DIBANGUN] BELUM DIBANGUN**  
> **Prioritas: Dibangun bersamaan Module B & C**  
> **Estimasi Build Time: 2-3 jam**

### Objektif
Menganalisis kompetitor percetakan di Makassar dan mengisi sheet Matriks Kompetitor.

### Data Points per Kompetitor

| Data Point | Sumber | Cara Ekstrak |
|------------|--------|-------------|
| Nama Kompetitor | Google Maps | Otomatis dari Module B |
| Fokus Layanan Utama | GMaps + IG | Parsing kategori & bio |
| Celah Kualitas | Google Maps Reviews | Filter review negatif, kata kunci: "warna", "kualitas", "jelek", "buram" |
| Celah SOP/Admin | Google Maps Reviews | Filter review negatif, kata kunci: "lambat", "lama", "admin", "respon" |
| Estimasi Kapasitas | GMaps + IG | Dari jam operasional, jumlah review, post frequency |
| Estetika Visual | Instagram | Manual assessment dari portfolio IG |

### Review Analysis (Tanpa LLM)
Karena tidak bisa pakai LLM, analisis review dilakukan dengan **keyword matching:**

```python
QUALITY_KEYWORDS = [
    "warna meleset", "warna beda", "kualitas jelek", "buram", "pudar",
    "tipis", "sobek", "tidak rapi", "berantakan", "luntur", "garis",
]

SOP_KEYWORDS = [
    "lambat", "lama", "admin tidak respon", "susah dihubungi",
    "tidak tepat waktu", "telat", "salah cetak", "salah ukuran",
    "tidak ramah", "ribet", "prosesnya lama",
]
```

---

## 12. Data Schema (Google Sheets)

### Sheet 1: Radar Prospek (Lead Generation)

| Kolom | Tipe | Deskripsi | Contoh |
|-------|------|-----------|--------|
| A: Entitas Bisnis | String | Nama bisnis | "Kopi Kenangan Makassar" |
| B: Kategori Segmen | String | Jenis bisnis | "F&B - Cafe" |
| C: Trigger Event | String | Kenapa jadi lead | "Baru buka 2 bulan" |
| D: Sumber Data | String | Platform asal data | "google_maps" / "instagram" / "tiktok" |
| E: Kontak | String | No. telp / IG / email | "0811-xxxx-xxxx" |
| F: Proyeksi Kebutuhan | String | Estimasi kebutuhan cetak | "Menu, banner, stiker" |
| G: Skor Prospek | Integer (1-10) | Hasil scoring engine | "8" |
| H: Status Akuisisi | String | Status follow-up | "BARU" / "CONTACTED" / "DEAL" / "REJECT" |
| I: URL Referensi | String | Link ke GMaps/IG/TikTok | "https://maps.google.com/..." |
| J: Tanggal Scrape | Date | Kapan data diambil | "2026-10-14" |
| K: Catatan | String | Notes manual dari owner | "" |

### Sheet 2: Matriks Kompetitor

| Kolom | Tipe | Deskripsi | Contoh |
|-------|------|-----------|--------|
| A: Nama Kompetitor | String | Nama percetakan | "XYZ Printing Makassar" |
| B: Fokus Layanan Utama | String | Spesialisasi | "Banner, spanduk, baliho" |
| C: Celah Kualitas | String | Keluhan dari review | "Warna sering meleset (3 review)" |
| D: Celah SOP/Admin | String | Keluhan operasional | "Admin lambat respon (5 review)" |
| E: Estimasi Kapasitas | String | Perkiraan skala | "Kecil-Menengah, 50 review" |
| F: Estetika Visual | String | Kualitas visual IG | "Rendah / Sedang / Tinggi" |
| G: Rating GMaps | Float | Rating Google Maps | "3.8" |
| H: Jumlah Review | Integer | Total review | "127" |
| I: Akun Instagram | String | Username IG | "@xyzprinting" |
| J: Website | String | URL website | "https://xyzprinting.com" |
| K: Harga Referensi | String | Jika terdeteksi | "Banner mulai 25rb/m²" |
| L: Tanggal Update | Date | Terakhir di-update | "2026-10-14" |

### Sheet 3: Market Signals (BARU)

| Kolom | Tipe | Deskripsi | Contoh |
|-------|------|-----------|--------|
| A: Signal | String | Apa yang terdeteksi | "Video viral cetak stiker" |
| B: Platform | String | Dari mana | "tiktok" |
| C: Metrik | String | Engagement numbers | "500K views, 10K likes" |
| D: Relevansi | String | Hubungan ke bisnis | "Demand stiker custom naik" |
| E: URL | String | Link ke konten | "https://tiktok.com/..." |
| F: Tanggal | Date | Kapan ditemukan | "2026-10-14" |

### Sheet 4: Scrape Log (BARU)

| Kolom | Tipe | Deskripsi |
|-------|------|-----------|
| A: Timestamp | DateTime | Kapan scraping dijalankan |
| B: Module | String | Module mana yang jalan (B/C/D) |
| C: Platform | String | google_maps / instagram / tiktok |
| D: Query | String | Search query yang digunakan |
| E: Results Count | Integer | Jumlah data yang diekstrak |
| F: Status | String | SUCCESS / PARTIAL / FAILED |
| G: Error Message | String | Detail error jika gagal |
| H: Duration (sec) | Integer | Lama proses |

---

## 13. Struktur Direktori

```
DATA CALON CUSTOMER/
├── intelligence_pipeline_prd.md     ← DOKUMEN INI (Single Source of Truth)
│
├── hermes-mcp-server/               ← Module A ([SELESAI] SELESAI)
│   ├── server.py                     # MCP Server (Google Sheets)
│   ├── init_pipeline_sheets.py       # Script inisialisasi sheets
│   ├── requirements.txt              # Dependencies Module A
│   ├── .env.example                  # Template environment vars
│   ├── .env                          # Actual env vars (git-ignored)
│   ├── credentials/                  # GCP Service Account JSON
│   └── logs/                         # Server logs
│
├── scrapers/                         ← Module B, C, D (AKAN DIBANGUN)
│   ├── __init__.py
│   ├── config.py                     # Shared config (queries, keywords, delays)
│   ├── utils.py                      # Shared utilities (rate limiting, logging)
│   ├── schemas.py                    # Data schemas & validation
│   │
│   ├── gmaps_scraper.py              # Module B: Google Maps
│   ├── instagram_scraper.py          # Module C: Instagram
│   ├── tiktok_scraper.py             # Module D: TikTok
│   │
│   ├── lead_scorer.py                # Module E: Lead Scoring Engine
│   ├── competitor_analyzer.py        # Module F: Competitor Matrix
│   │
│   └── requirements.txt              # Dependencies scraper modules
│
├── run_pipeline.py                   ← Entry point utama
│                                       python run_pipeline.py gmaps
│                                       python run_pipeline.py instagram
│                                       python run_pipeline.py tiktok
│                                       python run_pipeline.py all
│                                       python run_pipeline.py score
│
└── data/                             ← Local cache (git-ignored)
    ├── raw/                          # Raw scraping results (JSON)
    └── processed/                    # Processed & scored data
```

---

## 14. Fase Implementasi

### Fase 1: Google Maps Pipeline (Hari 1-2)
| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 1.1 | Install Scrapling + browser deps | Environment ready | 30 menit |
| 1.2 | Buat `scrapers/config.py` dengan queries | Config file | 30 menit |
| 1.3 | Buat `scrapers/gmaps_scraper.py` | Google Maps scraper working | 2 jam |
| 1.4 | Buat `scrapers/lead_scorer.py` | Scoring engine | 1 jam |
| 1.5 | Integrasikan output ke Google Sheets via MCP | Data masuk Sheets | 1 jam |
| 1.6 | Test run: scrape "cafe baru Makassar" | Validasi end-to-end | 30 menit |
| **Milestone:** | **Google Maps data pertama masuk Google Sheets** | | |

### Fase 2: Instagram Pipeline (Hari 3)
| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 2.1 | Buat `scrapers/instagram_scraper.py` | IG scraper working | 3 jam |
| 2.2 | Buat `scrapers/competitor_analyzer.py` | Review analyzer | 2 jam |
| 2.3 | Test: scrape 5 kompetitor dari hasil GMaps | Validasi stealth works | 1 jam |
| **Milestone:** | **Competitor IG data masuk Matriks Kompetitor** | | |

### Fase 3: TikTok + Polish (Hari 4-5)
| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.1 | Buat `scrapers/tiktok_scraper.py` | TikTok scraper working | 3 jam |
| 3.2 | Buat `run_pipeline.py` (unified runner) | CLI entry point | 1 jam |
| 3.3 | Update `init_pipeline_sheets.py` untuk sheet baru | Market Signals + Scrape Log | 30 menit |
| 3.4 | Dokumentasi README | User guide | 1 jam |
| 3.5 | Full test run semua module | Validasi pipeline lengkap | 1 jam |
| **Milestone:** | **Pipeline lengkap, siap digunakan rutin** | | |

### Total Estimasi: **3-5 hari kerja**

---

## 15. Risk Register

| # | Risiko | Probabilitas | Dampak | Mitigasi |
|---|--------|-------------|--------|----------|
| R1 | Instagram ban IP karena scraping | Medium | Tinggi | Rate limit ketat (15 page/session, 5s delay), frekuensi 1x/minggu maks |
| R2 | TikTok block stealth browser | Low-Medium | Sedang | StealthyFetcher + fallback ke manual |
| R3 | Google Maps perubahan DOM | Low | Rendah | Scrapling adaptive selectors auto-recover |
| R4 | RAM 8GB tidak cukup untuk StealthyFetcher | Low | Tinggi | Tutup semua app lain saat scraping, sequential only |
| R5 | Google Sheets API quota limit | Very Low | Rendah | Batch writes, bukan per-row |
| R6 | Data tidak akurat (false positives) | Medium | Sedang | Manual review oleh owner, scoring filter |
| R7 | Scrapling library breaking update | Low | Sedang | Pin version di requirements.txt |

---

## 16. Success Metrics

### Quantitative (Terukur)
| Metrik | Target Fase 1 | Target Bulan 1 | Target Bulan 3 |
|--------|---------------|-----------------|-----------------|
| Leads dari Google Maps | 50+ | 200+ | 500+ |
| Competitor profiles mapped | 10+ | 15+ | 20+ |
| Lead → Contacted conversion | — | 20% | 30% |
| Lead → Deal conversion | — | 5% | 10% |
| Scrape success rate | 80%+ | 90%+ | 95%+ |

### Qualitative (Kualitatif)
- Owner bisa lihat **leads baru** di Google Sheets setiap minggu
- Owner tahu **kelemahan kompetitor** untuk digunakan sebagai selling point
- Proses menemukan calon customer berubah dari **manual** ke **data-driven**

---

## 17. Keputusan Arsitektur (ADR)

### ADR-001: Scrapling sebagai Core Framework
- **Keputusan:** Gunakan Scrapling sebagai satu-satunya scraping framework
- **Alasan:** 
  - Menggantikan kebutuhan 5+ tools terpisah (BeautifulSoup, Selenium, Playwright, instagrapi, dll)
  - 87.5K stars, actively maintained, Python native
  - Built-in adaptive selectors, stealth bypass, MCP server
  - Ringan, bisa jalan di 8GB RAM
- **Trade-off:** Tidak se-spesifik scraper dedicated per-platform, tapi fleksibilitas lebih tinggi
- **Konsekuensi:** Semua scraper modules HARUS menggunakan Scrapling API

### ADR-002: Google Sheets sebagai Database
- **Keputusan:** Gunakan Google Sheets (bukan SQLite/PostgreSQL)
- **Alasan:**
  - Sudah ada infrastructure (MCP server + Service Account)
  - Owner bisa lihat & edit data langsung tanpa tools tambahan
  - Gratis dalam quota
  - Cocok untuk volume data sedang (100-500 rows/bulan)
- **Trade-off:** Tidak scalable untuk >10K rows; query lambat dibanding SQL
- **Konsekuensi:** Jika volume > 5K rows, pertimbangkan migrasi ke SQLite

### ADR-003: Sequential Execution (Bukan Concurrent)
- **Keputusan:** Hanya 1 module jalan pada satu waktu
- **Alasan:** RAM 8GB tidak cukup untuk multiple headless browsers
- **Trade-off:** Lebih lambat (tapi karena frekuensi 1x/minggu, ini tidak masalah)
- **Konsekuensi:** `run_pipeline.py all` menjalankan modules secara sequential

### ADR-004: Rule-Based Scoring (Bukan AI/LLM)
- **Keputusan:** Lead scoring dan review analysis pakai keyword matching, bukan LLM
- **Alasan:** Budget Rp 0, RAM 8GB tidak cukup untuk model lokal
- **Trade-off:** Kurang nuanced dibanding LLM analysis
- **Konsekuensi:** Scoring mungkin perlu tuning manual berdasarkan experience
- **Future:** Jika budget berubah, bisa tambahkan Gemini API free tier untuk enhance scoring

### ADR-005: No Proxy (Direct IP)
- **Keputusan:** Scraping tanpa proxy, menggunakan IP langsung
- **Alasan:** Budget Rp 0
- **Trade-off:** Risiko ban lebih tinggi di Instagram/TikTok
- **Mitigasi:** Rate limiting sangat ketat + frekuensi rendah (1x/minggu)
- **Future:** Jika ada budget $5-15/bulan, tambahkan residential proxy

---

## 18. Referensi & Repo Open-Source

### Core (DIGUNAKAN)
| Repo | Kegunaan | URL |
|------|----------|-----|
| **Scrapling** | Core scraping framework | https://github.com/D4Vinci/Scrapling |
| **Scrapling Docs** | Full documentation | https://scrapling.readthedocs.io |

### Cadangan (JIKA SCRAPLING TIDAK CUKUP)
| Repo | Kegunaan | URL |
|------|----------|-----|
| omkarcloud/google-maps-scraper | Dedicated GMaps scraper | https://github.com/omkarcloud/google-maps-scraper |
| ramasedang/e-commerce-scraping-api | Shopee/Tokped (nanti) | https://github.com/ramasedang/e-commerce-scraping-api |
| SSujitX/facebook-pages-scraper | Facebook pages (nanti) | https://github.com/SSujitX/facebook-pages-scraper |

### Future Expansion (BELUM DIGUNAKAN)
| Repo | Kegunaan | Kapan |
|------|----------|-------|
| ScrapeGraphAI | AI-powered parsing | Jika ada budget LLM API |
| browser-use | AI browser agent | Jika ada budget LLM API |
| Firecrawl | Web → Markdown | Jika ada budget + RAM |

---

> [!NOTE]
> **Dokumen ini adalah living document.** Update setiap kali ada perubahan keputusan, constraint, atau scope.
> 
> **Last Updated:** 14 Oktober 2026  
> **Version:** 2.0  
> **Author:** Owner + Hermes Agent (Brainstorming Session)