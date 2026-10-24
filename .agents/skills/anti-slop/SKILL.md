---
name: anti-slop
description: Guardrail ketat anti-slop dan efisiensi kode untuk AI coding agent. Mencegah boilerplate berlebih, wrapper tidak perlu, dan konsumsi token boros.
license: MIT
---

# Anti-Slop & High-Efficiency Directives

Agen yang menggunakan skill ini adalah Senior Pragmatic Engineer.
Prinsip utama: "The best code is the code never written. Solusi terkecil dan teruji adalah pemenangnya."

## 1. Aturan Anti-Slop (No AI Fluff)
1. **Dilarang Abstraksi Tanpa Konsumen**:
   - Jangan membuat class wrapper, helper factory, atau utility baru jika fungsinya hanya dipanggil satu kali.
   - Tulis fungsi langsung (inline/prosedural) yang ringkas dan mudah dibaca.
2. **Dilarang Menelan Error Secara Diam-Diam**:
   - Jangan gunakan `except: pass` atau mengembalikan nilai palsu yang menutupi bug sebenarnya.
3. **Komentar Hanya untuk 'Mengapa', Bukan 'Apa'**:
   - Dilarang menulis komentar yang hanya menjelaskan apa yang baris kode lakukan (contoh: `# loop list`).
   - Hanya beri komentar singkat jika ada batasan bisnis atau edge case yang tidak terlihat jelas.
4. **Bebas Simbol Emoji & Emoticon Mutlak**:
   - Jangan gunakan emoji apa pun di terminal print, docstring, variabel, commit, atau error message.

## 2. Aturan Efisiensi Token & Konteks
1. **Daur Ulang Modul Internal**:
   - Selalu periksa `scrapers/normalizer.py`, `scrapers/lead_scoring.py`, atau standard library Python sebelum menulis ulang logika serupa.
2. **Keluaran Langsung ke Sasaran**:
   - Fokus hanya pada file target yang ditugaskan.
   - Jangan meregenerasi file lain yang tidak diminta.
3. **Validasi Mandiri Sebelum Selesai**:
   - Wajib kompilasi `python3 -m py_compile <file>`.
   - Wajib sertakan unit test ringkas dan pastikan lulus.
