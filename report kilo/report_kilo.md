# Analisis Lengkap Sistem Scaping RUANG VISUAL
## Audit multidisiplin: Marketing — Scraping — Full-Stack Development

---

## 1. SCRAPING ENGINE (Kekurangan & Rekomendasi)

### 1.1 Gap Ekstraksi Data Multi-Platform

| Platform | Status | Kekurangan | Rekomendasi |
|----------|--------|------------|-------------|
| **Google Maps** | Fungsional | Hanya Makassar (harvest_makassar.py) | Ekspansi ke kota strategis: Bandung, Surabaya, Medan, Bali |
| **Instagram** | Terbatas | Data business_phone_number tidak bisa diakses via Crawlee/Playwright publik | Integrasi Apify Actor `apify/instagram-profile-scraper` atau `instagrapi` |
| **TikTok** | Mock data | Menggunakan `MOCK_DATA` Hardcoded — tidak scraping aktif | Implementasi Crawlee + Playwright atau Apify TikTok Shop actor |
| **Threads** | Mock data | Simulasi sederhana — tidak ada scraping aktif | Gunakan Apify `threads-scraper` atau scraping HTML publik |
| **Food Delivery** | Mock data | GoFood/GrabFood/ShopeeFood menggunakan data dummy | Integrasi Apify Food Delivery actors |
| **Meta Ads Library** | Fungsional | Hanya query berdasarkan keyword, tidak tracking per brand | Tambahkan tracking per brand/company name |

### 1.2 Gap Validasi & Verifikasi

**Kekurangan:**
- Tidak ada verifikasi nomor WhatsApp aktif (dead number detection)
- Tidak ada validasi keberadaan fisik toko (fake listing detection)
- Tidak ada cross-platform deduplication yang robust

**Rekomendasi:**
- Implementasi `wa-verify` library untuk cek ketersediaan nomor WhatsApp
- Tambahkan validasi Google Maps Place ID (is_active check via Maps API)
- Gunakan `fuzzywuzzy` untuk merge entitas duplikat

---

## 2. INTELLIGENCE ENGINE (Lead Scoring)

### 2.1 Formula 4 Pillars — Validasi PRD v2.0 Bab 5

**Sudah correct:**
- Legitimacy (25%): Place ID + Rating + Alamat
- Velocity (25%): Posting frequency (7/14/30 hari)
- Turnover (30%): Category-based weight (FNB/Fashion/Skincare = 30 poin)
- Budget (20%): Meta Ads active + Paid domain

**Kekurangan:**
- Tidak ada penalization factor untuk inactive accounts > 30 hari
- Tidak ada bonus untuk engagement rate tinggi (viral potential)
- Tidak ada penalty untuk negative reviews > 20%

**Rekomendasi:**
- Kurangi 5 poin jika `last_post_date > 30 hari`
- Tambahkan bonus +5 poin jika `avg_engagement_rate > 8%`
- Kurangi 3 poin per negative review (>5 negative = -15 poin cap)

### 2.2 Pain Points Extraction

**Sudah good:**
- Keyword matching untuk bocor, rembes, robek, dll.
- Mapping ke sales angle RUANG VISUAL

**Gap:**
- Tidak ada NLP sentiment analysis (positive/negative intensity)
- Tidak ada frequency counting per pain point

**Rekomendasi:**
- Gunakan `textblob` atau `vaderSentiment` untuk sentiment score
- Tampilkan top 5 pain points paling sering muncul per category

---

## 3. DASHBOARD & FRONTEND

### 3.1 Data Refresh Strategy

**Kekurangan:**
- Dashboard menggunakan static `SAMPLE_LEADS` hardcoded
- Tidak ada auto-refresh interval
- Tidak ada websocket untuk real-time updates

**Rekomendasi:**
- Pindahkan `SAMPLE_LEADS` ke file JSON terpisah
- Implementasi `setInterval` 5 menit untuk auto-refresh leads
- Gunakan `socket.io` untuk real-time notification

---

## 4. DATA PIPELINE & ARCHITECTURE

### 4.1 Workflow Pipeline

**Pipeline saat ini:**
```
Google Maps → Raw Data → Entity Matcher → Unified Dossier → Lead Scoring → Export CSV
```

**Gap:**
- Tidak ada data lineage tracking (siapa scrape, kapan, source)
- Tidak ada error handling untuk failed scrape
- Tidak ada retry mechanism

**Rekomendasi:**
- Tambahkan metadata `scraped_at`, `scraper_version`, `source_platform`
- Implementasi `try-catch` block dengan `logging.error()` per platform scraper
- Tambahkan `data/failed/` folder untuk raw failed responses

### 4.2 Catalog Sync

**Sudah ada:**
- `scrapers/sync_catalog.py` dan `data/catalog/ruang_visual_catalog.json`

**Gap:**
- Tidak ada auto-sync when catalog changed
- Tidak ada versioning untuk catalog changes

**Rekomendasi:**
- Gunakan `watchdog` untuk auto-reload catalog saat file berubah
- Tambahkan `catalog_version` di JSON header

---

## 5. RELEVANSI BISNIS (Marketing Perspective)

### 5.1 Segmentation yang Mungkin Ditambahkan

**Rekomendasi:**
- **Tier A**: Skor > 85 + Meta Ads active + Weekly posting → Priority outreach
- **Tier B**: Skor 70-85 + Monthly posting → Follow-up dalam 7 hari
- **Tier C**: Skor < 70 atau > 30 hari inactive → Warm-up campaign
- **Tier D**: Dead number atau non-commercial → Exclude list

### 5.2 Dynamic Pitch Generation

**Sudah ada:**
- Template based on category (FN-B, Fashion, Skincare, Corporate)

**Gap:**
- Tidak ada personalization berdasarkan recent post topic
- Tidak ada A/B testing untuk pitch variants

**Rekomendasi:**
- Inject `top_post_tags` ke pitch: "Saya lihat Kak baru launching Cold Cup 16oz"
- A/B test: Pitch versi humor vs formal untuk conversion rate tracking

---

## 6. TECHNICAL DEBT & RISK

### 6.1 Security & Compliance

**Critical:**
- `SUPABASE_SERVICE_ROLE_KEY` di `.env` → violate Zero-Interference Guardrails (PRD v2.0 Section 7)
- Hardcoded credentials di `scrapers/database.py:16-17`

**Rekomendasi:**
- Gunakan `NEXT_PUBLIC_SUPABASE_ANON_KEY` saja (read-only)
- Pindahkan semua secret ke environment variables eksternal

### 6.2 Scalability

**Gap:**
- Dashboard server menggunakan `http.server` (single-thread, tidak production-ready)
- Tidak ada pagination server-side (load semua leads ke memory)
- Tidak ada caching layer (Redis/Memcached)

**Rekomendasi:**
- Migrate ke FastAPI/Flask dengan Gunicorn/Uvicorn
- Implementasi SQL pagination (`LIMIT 25 OFFSET 0`)
- Cache catalog JSON di Redis dengan TTL 1 jam

---

## 7. PRIORITAS IMPLEMENTASI (1-2-3 Week Plan)

### Week 1: Critical Fixes
- [ ] Pindahkan `SAMPLE_LEADS` ke JSON external file
- [ ] Fix database.py: gunakan `SUPABASE_ANON_KEY` read-only
- [ ] Implement dead number validation di normalizer.py
- [ ] Tambahkan error logging per scraper

### Week 2: Data Quality
- [ ] Implement cross-platform deduplication (`entity_matcher.py` enhancement)
- [ ] Integrate Apify Instagram scraper (business_phone_number)
- [ ] Tambahkan sentiment analysis untuk pain points
- [ ] Implement pagination server-side

### Week 3: Relevance & Scale
- [ ] Expand territory: Bandung, Surabaya, Medan, Bali
- [ ] Implement Tier A/B/C/D segmentation
- [ ] Add dynamic pitch personalization
- [ ] Migrate dashboard ke FastAPI

---

## 8. METRICS SUCCESS CRITERIA

| KPI | Target | Current | Gap |
|-----|--------|---------|-----|
| Lead Accuracy (valid contact) | > 85% | ~65% | +20% |
| Data Freshness (last 7 days) | > 90% | Unknown | Audit needed |
| Multi-channel coverage | > 60% | ~30% | +30% |
| Sales Conversion Rate | > 15% | Unknown | Baseline needed |
| Dashboard Load Time | < 2s | Unknown | Profile needed |

---


**Catatan untuk Tim Marketing:**
- Segmentasi Tier A/B/C/D untuk strategic prioritization
- Dynamic pitch injection berdasarkan top post tags
- A/B test pitch variants untuk optimize conversion
