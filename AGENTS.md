# RUANG VISUAL — Panduan dan Aturan Kolaborasi Multi-Agen

Dokumen ini adalah pedoman operasional wajib bagi seluruh agen kecerdasan buatan (Kilo dan Antigravity/Hermes) yang bekerja di repositori ini.

---

## 1. Pembagian Peran dan Tanggung Jawab

Sistem ini menggunakan arsitektur kolaborasi dua agen:

### A. Kilo (Peran: Builder & Scraper Specialist)
Tanggung jawab utama:
1. Menulis dan menyempurnakan modul scraper platform (Google Maps, Facebook Marketplace, TikTok, Instagram, Threads, dsb.).
2. Mengembangkan logika ekstraksi data (regex nomor telepon WhatsApp, parsing HTML/DOM, deteksi kategori usaha).
3. Mengembangkan fungsi kalkulasi skor prospek (Lead Scoring Engine) dan pengolahan data mentah.
4. Menambahkan kata kunci kueri baru di scrapers/config.py.
5. Menulis uji coba mandiri lokal untuk modul baru.

Batasan Kilo:
- Jangan mengubah arsitektur utama run_pipeline.py all secara sepihak.
- Jangan mengubah struktur menu atau alur scrapers/telegram_bot.py.
- Jangan mengubah konfigurasi hermes-mcp-server atau google_apps_script_beautifier.js tanpa persetujuan.
- Serahkan verifikasi akhir, integrasi pipeline lengkap, dan git commit kepada Antigravity.

### B. Antigravity / Hermes (Peran: Architect, Auditor & Integrator)
Tanggung jawab utama:
1. Menjaga integritas arsitektur sistem dan spesifikasi PRD.
2. Mengaudit kode yang ditulis oleh Kilo (kepatuhan aturan, deteksi bug, pengecekan schema drift).
3. Mengintegrasikan modul baru buatan Kilo ke dalam alur eksekusi terpadu run_pipeline.py all dan scrapers/telegram_bot.py.
4. Mengelola sinkronisasi Google Sheets melalui Hermes MCP Server.
5. Menjalankan pengetesan end-to-end, pemantauan error, dan pengelolaan Git commit.

---

## 2. Aturan Mutlak Format: Bebas Emoji dan Emoticon

Sesuai aturan di .agents/rules/no_emojis.md, dilarang keras menggunakan emoji atau emoticon dalam bentuk apa pun.
Aturan ini berlaku mutlak untuk:
1. Seluruh teks jawaban dan komunikasi kepada pengguna.
2. Penamaan file, folder, variabel, dan sheet (tab) spreadsheet.
3. Seluruh baris kode (komentar, log terminal, string literal, label, hyperlink, format teks).
4. Pesan notifikasi Telegram, email, dan template lainnya.
5. Format data output (CSV, JSON, database).

Gunakan bahasa formal, bersih, profesional, dan berbasis teks biasa tanpa ornamen simbol.

---

## 3. Standar Skema Data Google Sheets (Single Source of Truth)

Seluruh modul yang melakukan ekspor data ke Google Sheets WAJIB mematuhi skema baku berikut:

### Tab 1: "Radar Prospek" (14 Kolom)
Kolom A: Nama Bisnis
Kolom B: Kategori
Kolom C: Sumber Platform
Kolom D: Skor
Kolom E: Status
Kolom F: No. WhatsApp
Kolom G: Link WA
Kolom H: Proyeksi Kebutuhan Cetak
Kolom I: Pemicu Kebutuhan & Konteks
Kolom J: Alamat
Kolom K: Rating & Ulasan
Kolom L: Website
Kolom M: Link Sumber Asli
Kolom N: Tanggal

### Tab 2: "Matriks Kompetitor" (11 Kolom)
Kolom A: Nama Percetakan
Kolom B: Fokus Layanan Utama
Kolom C: Kapasitas / Skala
Kolom D: Rating & Ulasan
Kolom E: No. WhatsApp
Kolom F: Link WA
Kolom G: Celah Kualitas
Kolom H: Celah Pelayanan & SOP
Kolom I: Selling Point RUANG VISUAL
Kolom J: Website / Maps
Kolom K: Tanggal Update

### Tab 3: "Market Signals" (6 Kolom)
Kolom A: Sinyal / Tren Produk
Kolom B: Platform
Kolom C: Tingkat Demand
Kolom D: Peluang untuk RUANG VISUAL
Kolom E: Link Referensi (Wajib berupa URL yang valid)
Kolom F: Tanggal

PENTING: Kolom E pada Market Signals selalu diformat sebagai tombol tautan (misal: "Lihat Tren" atau "Buka Peta"). Jangan pernah menaruh teks narasi aksi di Kolom E.

---

## 4. Standar Penulisan Modul Python Baru

Setiap modul scraper atau skrip baru di dalam folder scrapers/ WAJIB memenuhi standar:
1. Injeksi Path Root di Baris Teratas:
```python
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
```
2. Inisialisasi Browser Stealth:
Gunakan launch_stealth_browser(p) dari scrapers.utils, dan buat context secara eksplisit:
```python
browser = launch_stealth_browser(p)
context = browser.new_context(
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    viewport={"width": 1280, "height": 800}
)
```
3. Penyimpanan Data Lokal:
Data mentah disimpan di data/raw/, dan data terproses disimpan di data/processed/.
4. Flag Dukungan CLI:
Setiap scraper wajib mendukung argumen --mode, --limit, dan --dry-run.

---

## 5. Prosedur Penyelesaian Tugas Kilo

Setelah menyelesaikan penulisan atau pengubahan kode, Kilo harus:
1. Memvalidasi sintaks dengan menjalankan:
   python3 -m py_compile <file_yang_diubah>
2. Menjalankan pengetesan lokal dengan opsi --dry-run.
3. Memberikan laporan ringkas kepada pengguna dan merekomendasikan agar Antigravity melakukan audit dan integrasi ke pipeline utama.

---

## 6. Standar Efisiensi Kode (Ponytail Lean Code Standard)

Sesuai aturan di .agents/rules/ponytail_lean_code.md dan skill ponytail di .agents/skills/ponytail/:
1. Filosofi Inti: "The best code is the code you never wrote." Selesaikan masalah dengan penambahan kode seminimal mungkin.
2. Daur Ulang Pustaka Internal: Wajib menggunakan fungsi yang sudah ada di scrapers/utils.py dan scrapers/contact_enricher.py. Dilarang menulis ulang fungsi regex telepon, delay, logging, atau normalisasi.
3. Utamakan Standard Library: Gunakan urllib, re, json, pathlib sebelum mengusulkan dependensi baru.
4. Tolak Over-Engineering: Dilarang membuat abstraksi atau class wrapper berlebihan jika sebuah fungsi sederhana sudah cukup.
5. Ketersediaan Skill: Agen dapat mengaktifkan skill `.agents/skills/ponytail/`, `.agents/skills/ponytail-review/`, dan `.agents/skills/test-driven-development/` untuk memandu penulisan dan peninjauan kode bersih.

