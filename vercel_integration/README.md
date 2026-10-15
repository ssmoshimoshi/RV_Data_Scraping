# Panduan Integrasi Telegram Webhook ke Vercel (Opsi A)
## RUANG VISUAL — Mobile Intelligence Control

Panduan ini menghubungkan Telegram Bot langsung ke web app Vercel kamu (`ruang-visual-app.vercel.app`), sehingga kamu bisa memicu dan mengontrol scraping pipeline langsung dari ponsel.

---

## 1. Salin File Webhook ke Proyek Web App Vercel Kamu

Pilih salah satu sesuai struktur router pada proyek Next.js `ruang-visual-app`:

- **Jika menggunakan App Router (Next.js 13/14+):**
  Salin file `route.js` ke:
  `app/api/telegram-webhook/route.js`

- **Jika menggunakan Pages Router:**
  Salin file `api_telegram_webhook.js` ke:
  `pages/api/telegram-webhook.js`

---

## 2. Tambahkan Environment Variables di Vercel Dashboard

Buka dashboard Vercel proyek `ruang-visual-app` -> Settings -> Environment Variables, lalu tambahkan:

1. `TELEGRAM_BOT_TOKEN`
   Isi: `8826516320:AAEHnjqrAjJZHFUb9w3X8Mqd80iIoqEP4LA`

2. `GITHUB_REPO`
   Isi: `ssmoshimoshi/RV_Data_Scraping`

3. `GITHUB_PAT`
   Isi: Personal Access Token GitHub kamu (dengan izin `repo` dan `workflow`).
   Token ini diperlukan agar Vercel dapat memanggil GitHub Actions API saat kamu mengirim pesan di Telegram.

Setelah menambahkan variabel, lakukan redeploy proyek di Vercel agar perubahan aktif.

---

## 3. Daftarkan URL Webhook ke Telegram

Buka terminal atau browser kamu, lalu jalankan perintah berikut (ganti domain jika berbeda):

```bash
curl -F "url=https://ruang-visual-app.vercel.app/api/telegram-webhook" https://api.telegram.org/bot8826516320:AAEHnjqrAjJZHFUb9w3X8Mqd80iIoqEP4LA/setWebhook
```

Jika berhasil, Telegram akan mengembalikan respons:
`{"ok":true,"result":true,"description":"Webhook was set"}`

---

## 4. Daftar Perintah Bot Telegram dari Handphone

Setelah terpasang, kamu bisa mengetikkan perintah berikut langsung di grup Telegram:

- `/menu` atau `/help`
  Menampilkan panduan dan daftar perintah lengkap.

- `/semua`
  Menjalankan seluruh siklus pipeline di cloud (Google Maps, FB Marketplace, Instagram, TikTok, Matriks Kompetitor) dan mengirimkan laporan eksekutif lengkap ke grup Telegram.

- `/prospek`
  Menjalankan pencarian prospek bisnis baru berbasis radius workshop Rappocini dan 9 sektor usaha.

- `/pasar_fb`
  Menjalankan scraping khusus Facebook Marketplace Makassar untuk mendeteksi UMKM kuliner, fashion, dan kemasan polos.

- `/kompetitor`
  Menjalankan analisis harga dan pemetaan kelemahan percetakan kompetitor.

- `/tren`
  Menjalankan pemindaian produk printing viral dan peluang kemasan custom.

- `/bersihkan`
  Mengirim perintah ke Google Sheets untuk menghapus baris data uji coba lama agar lembar kerja kembali bersih.

- `/status`
  Mengecek kesiapan sistem dan menampilkan tautan langsung ke Google Sheets.
