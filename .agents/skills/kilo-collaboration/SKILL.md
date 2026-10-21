---
name: kilo-collaboration
description: Panduan prosedur standar audit, review, dan integrasi hasil kerja agen Kilo ke dalam arsitektur Ruang Visual.
---

# Kilo Collaboration & Quality Assurance Workflow

Skill ini digunakan oleh Antigravity untuk meninjau, menguji, dan mengintegrasikan kode yang baru saja dikerjakan oleh Kilo.

## Tahapan Prosedur Audit

1. **Pemeriksaan Bebas Emoji**:
   Pastikan tidak ada karakter emoji atau emoticon pada file yang baru diubah atau dibuat.
   Gunakan script verifikasi jika diperlukan:
   ```bash
   python3 -c 'import re, sys; p = re.compile(r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b55\u200d\ufe0f]"); ...'
   ```

2. **Pemeriksaan Skema Data Google Sheets**:
   Pastikan header yang digunakan di modul scraper tepat 100% mengikuti standar:
   - Radar Prospek (12 kolom)
   - Matriks Kompetitor (11 kolom)
   - Market Signals (6 kolom, dengan Kolom E sebagai Link Referensi URL)

3. **Pemeriksaan Injeksi sys.path**:
   Pastikan setiap skrip di scrapers/ menyertakan injeksi root path agar dapat dijalankan secara mandiri.

4. **Pemeriksaan Inisialisasi Playwright**:
   Pastikan launch_stealth_browser(p) dipanggil dengan benar tanpa salah unpacking.

5. **Integrasi ke Orkestrasi Utama**:
   - Daftarkan fungsi pemanggilan di run_pipeline.py (pada menu CLI dan run_all).
   - Daftarkan perintah terkait di scrapers/telegram_bot.py.

6. **Verifikasi Sintaks & Uji Kering**:
   - python3 -m py_compile <files>
   - scrapers/.venv/bin/python run_pipeline.py <module> --dry-run
