# RUANG VISUAL — Panduan dan Aturan Kolaborasi Multi-Agen

Dokumen ini adalah pedoman operasional wajib bagi seluruh agen kecerdasan buatan (Kilo dan Antigravity) yang bekerja di repositori ini.

---

## 1. Pembagian Peran dan Tanggung Jawab

Sistem ini menggunakan arsitektur kolaborasi dua agen:

### A. Kilo (Peran: Builder & Scraper Specialist)
Tanggung jawab utama:
1. Menulis dan menyempurnakan modul scraper platform di folder `scrapers/` (Instagram, Google Maps, TikTok, Meta Ads, Threads, Food Delivery Apps).
2. Mengimplementasikan mesin ekstraksi menggunakan Crawlee Python, `curl_cffi` (TLS client impersonation), dan `instagrapi` untuk operasi yang memerlukan sesi akun.
3. Mengembangkan fungsi normalisasi nomor WhatsApp (format `628xxxxxxxxxx`), sanitasi alamat, dan deteksi kategori usaha.
4. Mengembangkan fungsi kalkulasi skor prospek (`lead_scoring.py`) sesuai formula yang didefinisikan secara tunggal di PRD v2.0 Bab 5.
5. Menulis unit test mandiri di folder `tests/` dan menguji seluruh modul baru dengan flag `--dry-run`.

Batasan Kilo:
- Dilarang keras mengubah arsitektur atau komponen dashboard Next.js (`/market-scraping`) tanpa persetujuan eksplisit Antigravity.
- Dilarang menjalankan skrip produksi yang menulis ke database Supabase tanpa mode `--dry-run` terlebih dahulu.
- Dilarang mengubah skema DDL Supabase secara sepihak.
- Wajib memvalidasi sintaks sebelum serah terima: `python3 -m py_compile <file_yang_diubah>`.
- Serahkan verifikasi akhir, integrasi ke dashboard, dan git commit kepada Antigravity.

### B. Antigravity (Peran: Architect, Auditor & Integrator)
Tanggung jawab utama:
1. Menjaga integritas arsitektur sistem dan spesifikasi PRD v2.0.
2. Mengaudit setiap modul yang ditulis Kilo (kepatuhan aturan, keamanan, efisiensi memori, ketiadaan emoji).
3. Mengembangkan frontend dashboard lokal Next.js di rute `/market-scraping` dengan styling CMYK RUANG VISUAL.
4. Mengelola konektivitas API Supabase dan routing handler Next.js.
5. Menghubungkan webhook Apify Cloud ke database Supabase.
6. Melakukan pengujian end-to-end, pemantauan error, dan pengelolaan Git commit.

---

## 2. Aturan Mutlak Format: Bebas Emoji dan Emoticon

Dilarang keras menggunakan emoji atau emoticon dalam bentuk apa pun.
Aturan ini berlaku mutlak untuk:
1. Seluruh teks jawaban dan komunikasi kepada pengguna.
2. Penamaan file, folder, variabel, dan kolom database.
3. Seluruh baris kode (komentar, log terminal, string literal, label).
4. Pesan notifikasi apa pun dan template komunikasi.
5. Format data output (JSON, database, log file).

Gunakan bahasa formal, bersih, profesional, dan berbasis teks biasa tanpa ornamen simbol.

---

## 3. Standar Penulisan Modul Python Baru

Setiap modul scraper atau skrip baru di dalam folder `scrapers/` WAJIB memenuhi standar berikut:

### 3.1 Injeksi Path Root di Baris Teratas
```python
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
```

### 3.2 Catatan Penting: Ekstraksi Kontak Instagram
Nomor WhatsApp dari tombol kontak profil bisnis Instagram (`business_phone_number`) TIDAK dapat diakses melalui Crawlee atau Playwright yang merender HTML publik. Data tombol kontak hanya tersedia melalui:
- **Apify Cloud Actor** (`apify/instagram-profile-scraper`) yang mengelola sesi akun secara internal.
- **Library `instagrapi` (Python)** menggunakan sesi akun bot yang telah tersimpan.

Kilo wajib menggunakan salah satu dari dua metode di atas untuk ekstraksi nomor kontak Instagram. Dilarang mencoba mengekstrak data ini via Playwright/Crawlee publik tanpa sesi.

### 3.3 Penyimpanan Data Lokal
- Data mentah disimpan di `data/raw/`.
- Data terproses disimpan di `data/processed/`.

### 3.4 Flag Dukungan CLI
Setiap scraper wajib mendukung argumen `--mode`, `--limit`, dan `--dry-run`.

---

## 4. Prosedur Penyelesaian Tugas Kilo

Setelah menyelesaikan penulisan atau pengubahan kode, Kilo harus:
1. Memvalidasi sintaks: `python3 -m py_compile <file_yang_diubah>`.
2. Menjalankan pengetesan lokal dengan opsi `--dry-run`.
3. Memberikan laporan ringkas kepada pengguna dan merekomendasikan agar Antigravity melakukan audit dan integrasi ke dashboard.

---

## 5. Standar Efisiensi Kode (Ponytail Lean Code Standard)

Sesuai aturan di `.agents/rules/ponytail_lean_code.md`:
1. Filosofi Inti: "The best code is the code you never wrote." Selesaikan masalah dengan penambahan kode seminimal mungkin.
2. Daur Ulang Internal: Wajib memeriksa apakah fungsi yang dibutuhkan sudah ada di modul lain sebelum menulis ulang.
3. Utamakan Standard Library: Gunakan `urllib`, `re`, `json`, `pathlib` sebelum mengusulkan dependensi baru.
4. Tolak Over-Engineering: Dilarang membuat abstraksi atau class wrapper berlebihan jika sebuah fungsi sederhana sudah cukup.
5. Ketersediaan Skill: Agen dapat mengaktifkan skill `.agents/skills/ponytail/`, `.agents/skills/ponytail-review/`, dan `.agents/skills/test-driven-development/` untuk memandu penulisan dan peninjauan kode bersih.

---

## 6. Dokumen Acuan Arsitektur

- **PRD v2.0 (Sumber Kebenaran Tunggal)**: `PRD_RUANG_VISUAL_MARKET_INTELLIGENCE.md`
  Bab 5 PRD adalah satu-satunya definisi resmi formula Lead Scoring Engine. Kilo wajib mengacu hanya ke dokumen ini.
- **Spesifikasi Titik Data per Platform**: `docs/flowcharts/DETAIL_EKSTRAKSI_MULTIPLATFORM.md`
- **Diagram Alur Arsitektur**: `docs/flowcharts/`

---

## 7. Protokol Larangan Mutlak Akses Database Produksi (Zero-Interference Guardrails)

Untuk menjamin integritas dan kelancaran aplikasi produksi utama (`ruang-visual-app.vercel.app`), seluruh agen (Kilo dan Antigravity) WAJIB mematuhi aturan keamanan berikut:

### 7.1 Mode Akses Wajib: Strictly Read-Only (Hanya SELECT)
- Modul perayap, skrip sinkronisasi, dan pipeline scraping HANYA boleh menjalankan query `SELECT` pada tabel katalog master:
  - `public.master_items`
  - `public.product_templates`
  - `public.product_template_items`
- DILARANG KERAS menjalankan operasi mutasi: `INSERT`, `UPDATE`, `DELETE`, `UPSERT`, atau `TRUNCATE` pada tabel apa pun di database produksi.
- DILARANG KERAS menjalankan perintah DDL: `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, atau mengubah skema dan trigger produksi.

### 7.2 Pembatasan Kredensial (Principle of Least Privilege)
- Repositori ini hanya diperbolehkan menggunakan `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- DILARANG menggunakan atau menyimpan `SUPABASE_SERVICE_ROLE_KEY` produksi pada repositori ini agar hak akses tetap dibatasi oleh proteksi Row-Level Security (RLS).

### 7.3 Pemisahan Database Prospek (Database Isolation)
- Data calon pelanggan (leads mentah, hasil scraping, status outreach, skor prospek) DILARANG disimpan di database produksi utama.
- Seluruh data intelijen pasar disimpan secara terisolasi di repositori lokal (`data/raw/` dan `data/processed/`).

### 7.4 Snapshot Cache Lokal (Zero Live Traffic Impact)
- Dilarang memanggil API database produksi secara berulang dalam loop scraping atau operasional dashboard harian.
- Gunakan snapshot berkala (`data/catalog/ruang_visual_catalog.json`) yang diperbarui melalui modul `scrapers/sync_catalog.py`. Mesin penalar kebutuhan dan generator outreach wajib membaca berkas snapshot lokal ini.

### 7.5 Tabel Terlarang
- Seluruh agen DILARANG KERAS mengakses atau membaca tabel transaksi, operasional kasir, dan akuntansi:
  `orders`, `order_items`, `invoices`, `transactions`, `cash_book`, `users`, `payroll`, `debts`, `suppliers`.

