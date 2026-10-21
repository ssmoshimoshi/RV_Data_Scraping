# RUANG VISUAL — Panduan dan Acuan Kerja Agen Kilo

Dokumen ini adalah acuan instruksi kerja teknis operasional untuk Kilo (Builder & Scraper Specialist).
Seluruh pengembangan kode wajib mematuhi standar arsitektur sistem dan aturan kolaborasi multi-agen di AGENTS.md.

---

## 1. Aturan Mutlak Operasional

1. Bebas Emoji dan Emoticon 100%:
   Dilarang keras menyisipkan emoji atau emoticon dalam bentuk apa pun pada:
   - Seluruh baris kode (komentar, log terminal, string literal, regex, nama variabel).
   - Seluruh teks respon dan komunikasi kepada pengguna.
   - Seluruh file output data (JSON, CSV).
2. Standar Path Root di Baris Teratas Modul:
   Setiap modul baru di folder scrapers/ wajib menyertakan injeksi path:
   ```python
   import sys
   from pathlib import Path
   PROJECT_ROOT = Path(__file__).resolve().parent.parent
   if str(PROJECT_ROOT) not in sys.path:
       sys.path.insert(0, str(PROJECT_ROOT))
   ```
3. Browser Automation:
   Gunakan fungsi launch_stealth_browser(p) dari scrapers.utils dengan penanganan konteks eksplisit.
4. Jangan Mengubah Arsitektur Utama:
   Jangan mengubah alur run_pipeline.py all, scrapers/telegram_bot.py, atau konfigurasi Google Apps Script tanpa koordinasi. Verifikasi akhir dan integrasi pipeline dilakukan oleh Antigravity.

---

## 2. Daftar Tugas Prioritas Kilo

### Tugas 1: Modul Pengayaan Kontak (Web & Bio Link Enricher)
- Lokasi File: scrapers/web_enricher.py
- Tujuan: Menemukan nomor WhatsApp yang tersembunyi pada website bisnis atau link bio (Linktree, Beacons, Instagram bio) untuk calon pelanggan yang belum memiliki nomor telepon di Google Maps.
- Spesifikasi Teknis:
  1. Terima input berupa URL website bisnis atau link bio.
  2. Buka halaman target menggunakan requests/httpx atau stealth browser jika membutuhkan render DOM.
  3. Ekstraksi nomor WhatsApp menggunakan regex khusus tautan:
     - href wa.me/628... atau api.whatsapp.com/send?phone=...
     - Pola teks di footer atau halaman kontak (08xx, +628xx).
  4. Integrasikan hasil nomor dengan modul scrapers/contact_enricher.py menggunakan fungsi classify_phone_number.
  5. Sediakan CLI mandiri:
     ```bash
     python3 scrapers/web_enricher.py --limit 10 --dry-run
     ```

### Tugas 2: Penambang Celah Negatif Kompetitor (Competitor Review Mining)
- Lokasi File: scrapers/competitor_analyzer.py
- Tujuan: Menggali review bintang 1 sampai 3 dari kompetitor percetakan di Google Maps Makassar untuk dijadikan amunisi penawaran (selling point) RUANG VISUAL.
- Spesifikasi Teknis:
  1. Saat melakukan crawling profil kompetitor di Google Maps, klik tab ulasan (reviews) dan filter ulasan terendah (lowest rating).
  2. Ekstrak teks keluhan pelanggan (misal: pengerjaan lambat, warna sablon luntur, hasil potong miring, admin lambat membalas pesan).
  3. Kategorikan keluhan ke dalam 2 aspek:
     - Celah Kualitas (Quality Gap)
     - Celah Pelayanan & SOP (Service & SOP Gap)
  4. Buat fungsi pembuat narasi tanding:
     - Jika keluhan pengerjaan lambat -> Selling point: "Garansi selesai tepat waktu atau potongan biaya antar."
     - Jika keluhan warna pudar -> Selling point: "Menggunakan tinta pigment premium tahan cuci dan garansi cetak ulang."

### Tugas 3: Ekspansi Kata Kunci Kueri Pencarian Sektor Baru
- Lokasi File: scrapers/config.py
- Tujuan: Menambah variasi target pencarian Google Maps untuk koridor bisnis potensial di Makassar.
- Spesifikasi Teknis:
  Tambahkan kueri baru pada list GMAPS_LEAD_QUERIES untuk sektor:
  - Wedding venue dan studio foto di Makassar
  - Kantor distributor dan supplier bahan bangunan
  - Klinik gigi dan laboratorium medis swasta
  - Agensi periklanan dan konsultan bisnis

---

## 3. Prosedur Penyelesaian & Uji Mandiri

Sebelum melaporkan tugas selesai kepada pengguna, Kilo WAJIB melakukan:
1. Validasi Sintaks:
   ```bash
   python3 -m py_compile <file_yang_diubah_atau_dibuat>
   ```
2. Uji Coba Lokal Terbatas:
   Jalankan modul dengan opsi --limit 2 --dry-run dan pastikan tidak ada exception.
3. Laporan Ringkas:
   Laporkan apa saja yang telah dibangun secara singkat dan sarankan pengguna untuk meminta Antigravity melakukan audit serta integrasi ke pipeline utama.
