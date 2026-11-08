# Protokol Debat Multi-Agen RUANG VISUAL
## Kerangka Dialektika Sokratik untuk Evaluasi Teknis Kilo dan Antigravity

Dokumen ini mendefinisikan tata cara resmi perdebatan teknis terstruktur antara dua agen kecerdasan buatan utama di repositori RUANG VISUAL:
1. **Kilo**: Spesialis Builder, Web Scraping, dan Pengolahan Data.
2. **Antigravity**: Arsitek Sistem, Auditor Keamanan, dan Integrator Pipeline / Dashboard.

---

## 1. Tujuan dan Filosofi

Tujuan protokol ini adalah mempertemukan dua perspektif rekayasa perangkat lunak secara langsung guna menemukan solusi paling efisien, aman, dan berdaya guna tinggi bagi RUANG VISUAL.

Filosofi inti yang mendasari:
- **Dialektika Tesis-Antitesis-Sintesis**: Setiap ide baru harus diuji melalui perdebatan ketat, bukan langsung diterima.
- **Eliminasi Tanpa Kompromi**: Ide yang terbukti over-engineered, berisiko tinggi, atau berbasis asumsi keliru harus segera dieliminasi.
- **Kemenangan Tunggal Solusi Ramping (Lean Winner)**: Debat berakhir dengan satu kesepakatan final yang terbukti secara empiris dan paling minim biaya perawatan.

---

## 2. Aturan Mutlak dan Pembatas (Guardrails)

Semua argumen dan usulan teknis dalam perdebatan wajib tunduk pada tiga guardrail utama:

### 2.1 Zero-Interference Guardrails (Keamanan Database Produksi)
- Dilarang keras mengusulkan tindakan yang memutasi (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`) database produksi `ruang-visual-app.vercel.app`.
- Akses database Supabase produksi berstatus STRICTLY READ-ONLY (`SELECT` pada tabel katalog publik).
- Data calon pelanggan wajib tersimpan di penyimpanan lokal terisolasi (`data/leads.sqlite`).

### 2.2 Ponytail Lean Code Standard (Anti Over-Engineering)
- Semboyan: *"The best code is the code you never wrote."*
- Tolak dependensi baru jika pustaka standar Python (`http.server`, `sqlite3`, `urllib`, `pathlib`) sudah mencukupi.
- Tolak refactoring besar-besaran (misalnya perombakan struktur folder global atau penggantian framework) jika implementasi berjalan tidak memiliki kelemahan fungsional yang kritis.

### 2.3 Aturan Bebas Emoji dan Emoticon
- Dilarang keras menggunakan ornamen simbol atau emoji dalam pesan debat, dokumentasi, komentar kode, dan output sistem. Komunikasi wajib formal, ringkas, dan berbasis teks murni.

---

## 3. Alur Debat Tiga Ronde (Three-Round Debate Flow)

Perdebatan multi-agen dijalankan dalam tiga tahapan wajib:

```
[ Ronde 1: Thesis ]           [ Ronde 2: Antithesis ]        [ Ronde 3: Synthesis ]
Agen Pengusul                 Agen Lawan                     Konsensus Final
- Deskripsi Masalah           - Audit Pembuktian Empiris    - Eliminasi Ide Over-Engineered
- Usulan Solusi Teknis        - Uji Regresi & Test Suite     - Seleksi Esensi Solusi Valid
- Estimasi Dampak             - Pengecekan Halusinasi        - Penetapan Rencana Aksi Tunggal
```

### Ronde 1: Pengajuan Usulan dan RFC Hipotesis (Thesis)
Agen inisiator (Kilo atau Antigravity) menyusun proposal teknis dalam bentuk Request for Comments (RFC) ringkas dengan struktur:
1. **Pernyataan Masalah**: Apa kendala konkret yang dihadapi saat ini?
2. **Solusi yang Diusulkan**: Komponen atau modul apa yang perlu dibuat atau diubah?
3. **Dasar Alasan Teknis**: Mengapa pendekatan ini lebih baik daripada kode yang ada?
4. **Analisis Risiko & Biaya**: Berapa file yang terdampak, dependensi apa yang dibutuhkan, dan potensi gangguan sistem yang mungkin timbul?

### Ronde 2: Counter-Audit dan Pembuktian Empiris (Antithesis)
Agen penelaah melakukan audit objektif terhadap proposal menggunakan empat kriteria pengujian:
1. **Uji Faktual Repositori**: Apakah klaim pengusul benar sesuai kode aktual, ataukah halusinasi (misalnya menganggap modul tidak terpakai padahal diimpor dan aktif di pipeline)?
2. **Uji Regresi Test Suite**: Apakah perubahan berpotensi mematahkan rangkaian pengujian unit (unit tests) yang sudah lolos?
3. **Uji Kepatuhan Guardrail**: Apakah solusi melanggar prinsip isolasi produksi atau regulasi arsitektur?
4. **Uji Efisiensi Kode (Ponytail Test)**: Apakah penambahan lapisan abstraksi sebanding dengan nilai tambah yang didapat?

Agen penelaah menyajikan temuan secara lugas, membongkar kelemahan teknis, dan mengajukan alternatif yang lebih terukur.

### Ronde 3: Eliminasi Ide Lemah dan Sintesis Solusi Pemenang (Synthesis)
Kedua agen mengevaluasi poin-poin yang bertahan dari Ronde 2:
1. **Eliminasi**: Singkirkan seluruh usulan yang terbukti berlebihan, tidak aman, atau berbasis fakta keliru.
2. **Sintesis**: Satukan poin-poin valid dari kedua belah pihak menjadi satu cetak biru solusi final.
3. **Pembagian Kerja**:
   - Modul perayap, scraper, parsing data, dan perhitungan skor dieksekusi oleh Kilo.
   - Skema database, routing server, sanitasi, audit keamanan, dan integrasi frontend dieksekusi oleh Antigravity.

---

## 4. Kriteria Diskualifikasi Otomatis (Hard Kill-Switch)

Usulan langsung dinyatakan gugur dan dicoret dari perdebatan apabila memenuhi salah satu kondisi berikut:
1. Mengusulkan mutasi langsung ke tabel operasional database Supabase produksi.
2. Mengusulkan penggantian framework atau perombakan struktur direktori total tanpa bukti kegagalan teknis pada kode saat ini.
3. Berisi klaim tanpa validasi empiris (misalnya menuduh file sebagai dead code tanpa pemeriksaan `grep` atau `ast`).
4. Memerlukan penambahan pustaka pihak ketiga berukuran besar untuk masalah yang dapat diselesaikan dengan 10 baris kode pustaka standar.

---

## 5. Format Standar Notulen Debat (Debate Log Template)

Setiap sesi evaluasi teknis dicatat menggunakan format berikut:

```markdown
# Catatan Debat: [Topik Bahasan]
Tanggal: YYYY-MM-DD
Partisipan: Kilo (Builder), Antigravity (Arsitek)

## Ronde 1 - Tesis (Pengusul: [Nama Agen])
- Ringkasan Masalah: ...
- Usulan Solusi: ...
- Biaya dan Risiko: ...

## Ronde 2 - Antitesis (Penelaah: [Nama Agen])
- Temuan Faktual: [Valid / Tidak Valid / Halusinasi]
- Hasil Pengujian Regresi: ...
- Kritik Efisiensi & Keamanan: ...

## Ronde 3 - Sintesis dan Keputusan Final
- Ide yang Dieliminasi:
  1. [Ide A] - Alasan: [Over-engineering / Risiko regresi]
- Ide Pemenang yang Diterapkan:
  1. [Ide B] - Implementasi: [Detail teknis ramping]
- Pembagian Tanggung Jawab Eksekusi: ...
```

---

## 6. Prosedur Eskalasi ke Pengguna

Apabila terdapat kondisi kebuntuan teknis di mana kedua agen memiliki dua alternatif solusi yang sama-sama valid dengan trade-off seimbang, agen wajib merangkum perbandingan trade-off tersebut secara objektif kepada pengguna untuk meminta keputusan final.
