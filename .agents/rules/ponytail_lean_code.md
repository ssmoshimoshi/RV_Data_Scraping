# Aturan Efisiensi Kode (Ponytail Lean Code Standard)

Dokumen aturan ini wajib dipatuhi oleh seluruh agen (Kilo dan Antigravity/Hermes).
Filosofi utama: "The best code is the code you never wrote." Selesaikan seluruh masalah dengan penambahan baris kode sesedikit mungkin.

---

## 1. Tangga Keputusan Sebelum Menulis Kode (The Decision Ladder)

Setiap agen wajib menaiki tangga keputusan berikut sebelum menulis kode baru:
1. **YAGNI (You Aren'\''t Gonna Need It)**: Jangan pernah membuat fitur, abstraksi, opsi, atau konfigurasi tambahan yang tidak diminta oleh pengguna.
2. **Daur Ulang Kode Internal (Codebase Reuse)**: Selalu gunakan fungsi pembantu yang sudah ada di `scrapers/utils.py`, `scrapers/contact_enricher.py`, atau modul lainnya. Dilarang menulis ulang fungsi regex, delay, logging, atau normalisasi telepon.
3. **Pustaka Standar Python (Standard Library First)**: Utamakan modul bawaan (`urllib`, `re`, `json`, `pathlib`). Dilarang menginstal dependensi pip baru untuk hal sepele.
4. **Pustaka yang Sudah Terpasang**: Jika butuh scraping, gunakan `patchright` atau `requests`/`httpx` yang sudah ada di virtual environment.
5. **Solusi Paling Ringkas**: Pilihlah diff kode terpendek yang bekerja dengan benar dan mudah dibaca manusia.

---

## 2. Larangan Over-Engineering

- Dilarang membuat class wrapper atau inheritance berlapis jika sebuah fungsi biasa sudah cukup.
- Penghapusan kode usang (deletion) lebih baik daripada penumpukan kode baru (addition).
- Komentar kode hanya untuk menjelaskan alasan logis non-intuitif dalam 1 baris, bukan mengulang apa yang dilakukan kode.
- Sebelum memperbaiki bug fungsi bersama, periksa seluruh pemanggil (callers) menggunakan grep agar perbaikan dilakukan di akar masalah.

---

## 3. Batasan Mutlak yang Tidak Boleh Dipangkas

- Penanganan error (try/except) yang mencegah hilangnya data atau kegagalan pipeline.
- Validasi data pada batas input eksternal (regex nomor telepon, pembersihan format URL).
- Aturan baku bebas emoji dan emoticon (0 emoji).
- Skema baku Google Sheets dan standar single source of truth.
