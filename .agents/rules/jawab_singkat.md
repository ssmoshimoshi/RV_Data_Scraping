# Aturan Mode Respons Singkat (Trigger: "js")

## 1. Definisi Trigger
Kata kunci `js` (kependekan dari "jawab singkat") adalah pemicu formal untuk menghasilkan jawaban ringkas.

## 2. Ketentuan Deteksi
Aturan ini aktif apabila kata kunci `js` ditemukan pada salah satu posisi berikut:
1. **Di awal prompt**: Sebagai kata pertama atau awalan kalimat (contoh: "js apa kesimpulannya", "js, bagaimana status server").
2. **Di akhir prompt**: Sebagai kata terakhir atau penutup kalimat (contoh: "apakah deployment berhasil js", "berikan analisis performanya js").
3. Deteksi bersifat case-insensitive (`js`, `JS`, `Js`).

## 3. Perilaku Wajib Agen saat Mode "js" Aktif
1. **Langsung ke Inti**: Jawab langsung tanpa kalimat pengantar basa-basi, tanpa repetisi pertanyaan pengguna, dan tanpa kalimat penutup.
2. **Padat dan Ringkas**: Batasi penjelasan hanya pada fakta esensial, status, atau kesimpulan utama. Gunakan poin-poin pendek jika data lebih dari satu.
3. **Kepatuhan Invarian Sistem**: Mode singkat tetap tunduk pada larangan mutlak emoji/emoticon dan standar profesionalisme formal.
