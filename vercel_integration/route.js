/**
 * RUANG VISUAL — Telegram Webhook Handler (Next.js App Router)
 * ============================================================
 * Pasang file ini di web app Vercel kamu jika menggunakan App Router:
 * Path di Next.js: app/api/telegram-webhook/route.js
 *
 * Environment Variables yang dibutuhkan di Vercel:
 * 1. TELEGRAM_BOT_TOKEN : 8826516320:AAEHnjqrAjJZHFUb9w3X8Mqd80iIoqEP4LA
 * 2. GITHUB_PAT         : Personal Access Token GitHub (izin repo / workflow)
 * 3. GITHUB_REPO        : ssmoshimoshi/RV_Data_Scraping
 *
 * Bebas dari semua karakter emoji dan emoticon.
 */

import { NextResponse } from "next/server";

export async function POST(req) {
  try {
    const body = await req.json();
    const message = body?.message;

    if (!message || !message.text) {
      return NextResponse.json({ ok: true });
    }

    const chatId = message.chat.id;
    const text = message.text.trim();
    const botToken = process.env.TELEGRAM_BOT_TOKEN || "8826516320:AAEHnjqrAjJZHFUb9w3X8Mqd80iIoqEP4LA";
    const githubPat = process.env.GITHUB_PAT;
    const githubRepo = process.env.GITHUB_REPO || "ssmoshimoshi/RV_Data_Scraping";
    const sheetUrl = "https://docs.google.com/spreadsheets/d/1mDx0aQcz95iPN6KwdmRgb2RE2xVNIhAgiuoq96k6dAU/edit";

    async function sendTelegramMessage(textMsg) {
      try {
        await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_id: chatId,
            text: textMsg,
            parse_mode: "Markdown",
          }),
        });
      } catch (err) {
        console.error("Gagal mengirim pesan Telegram:", err);
      }
    }

    async function triggerGitHubWorkflow(mode, desc) {
      if (!githubPat) {
        await sendTelegramMessage(
          "Gagal memicu cloud: GITHUB_PAT belum dikonfigurasi di environment Vercel."
        );
        return false;
      }

      try {
        const response = await fetch(`https://api.github.com/repos/${githubRepo}/dispatches`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${githubPat}`,
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "RUANG-VISUAL-Vercel-Webhook",
          },
          body: JSON.stringify({
            event_type: "telegram_command",
            client_payload: {
              mode: mode,
              chat_id: String(chatId),
            },
          }),
        });

        if (response.status === 204 || response.ok) {
          await sendTelegramMessage(
            `Perintah diterima.\nSistem sedang menjalankan ${desc} di cloud.\nLaporan dan notifikasi akan dikirimkan otomatis ke grup ini setelah selesai.\n\nLink Spreadsheet: ${sheetUrl}`
          );
          return true;
        } else {
          const errText = await response.text();
          await sendTelegramMessage(
            `Gagal memicu GitHub Actions. Kode respons: ${response.status}. Detail: ${errText}`
          );
          return false;
        }
      } catch (err) {
        await sendTelegramMessage(`Error koneksi ke GitHub Actions: ${err.message}`);
        return false;
      }
    }

    const cmd = text.split(" ")[0].toLowerCase();

    switch (cmd) {
      case "/start":
      case "/help":
      case "/menu":
        const menu = [
          "*RUANG VISUAL — Market Intelligence Pipeline*",
          "Pusat Komando Mobile Makassar Focus",
          "--------------------------------------------------",
          "Daftar Perintah:",
          "/semua : Jalankan seluruh pipeline (Maps, FB, IG, TikTok, Matrix)",
          "/prospek : Jalankan pencarian prospek bisnis baru",
          "/pasar_fb : Jalankan scraping khusus Facebook Marketplace",
          "/kompetitor : Analisis harga dan matriks percetakan kompetitor",
          "/tren : Pemantauan produk printing viral & sinyal pasar",
          "/bersihkan : Bersihkan data lama di Google Sheets",
          "/status : Tampilkan link Google Sheets & status sistem",
          "--------------------------------------------------",
          `Spreadsheet: ${sheetUrl}`,
        ].join("\n");
        await sendTelegramMessage(menu);
        break;

      case "/semua":
        await triggerGitHubWorkflow("all", "Seluruh Rangkaian Pipeline Multi-Platform");
        break;

      case "/prospek":
        await triggerGitHubWorkflow("gmaps", "Scraper Prospek Google Maps (Radius Workshop)");
        break;

      case "/pasar_fb":
        await triggerGitHubWorkflow("facebook", "Facebook Marketplace Scraper Makassar");
        break;

      case "/kompetitor":
        await triggerGitHubWorkflow("matrix", "Analisis Matriks Kompetitor Percetakan");
        break;

      case "/tren":
        await triggerGitHubWorkflow("tiktok", "TikTok & Market Signals Trend Scraper");
        break;

      case "/bersihkan":
        await triggerGitHubWorkflow("clean-sheets", "Pembersihan Data Lama di Google Sheets");
        break;

      case "/status":
        await sendTelegramMessage(
          `*Status Sistem RUANG VISUAL*\nSemua layanan operasional aktif.\nData terbaru dapat dilihat langsung di Google Sheets:\n${sheetUrl}`
        );
        break;

      default:
        break;
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({ status: "RUANG VISUAL Webhook Active" });
}
