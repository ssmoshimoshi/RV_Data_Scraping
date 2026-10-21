"""
RUANG VISUAL — Telegram Bot Local Runner (Polling Engine)
=========================================================
Menjalankan bot Telegram secara langsung dari laptop untuk menerima perintah
mobile tanpa perlu menunggu deployment Vercel selesai.

Perintah yang didukung:
/menu, /help   : Tampilkan daftar perintah
/semua         : Jalankan seluruh pipeline (Maps, FB, IG, TikTok, Matrix)
/prospek       : Jalankan pencarian prospek Google Maps
/pasar_fb      : Jalankan scraping Facebook Marketplace Makassar
/kompetitor    : Jalankan analisis matriks kompetitor
/tren          : Jalankan pemantauan tren TikTok & produk printing
/bersihkan     : Bersihkan data lama di Google Sheets
/status        : Tampilkan status sistem dan tautan spreadsheet

Bebas dari seluruh karakter emoji dan emoticon.
"""

import sys
import json
import time
import threading
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.utils import get_logger, get_env_var

log = get_logger("telegram-bot")

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1mDx0aQcz95iPN6KwdmRgb2RE2xVNIhAgiuoq96k6dAU/edit"


def send_message(token: str, chat_id: str, text: str):
    """Kirim pesan teks ke chat Telegram via Bot API menggunakan mode HTML."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log.error(f"Gagal mengirim pesan Telegram: {e}")
        # Fallback jika ada tag HTML yang tidak valid
        try:
            plain_payload = json.dumps({
                "chat_id": chat_id,
                "text": text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", ""),
            }).encode("utf-8")
            plain_req = urllib.request.Request(url, data=plain_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(plain_req, timeout=15) as plain_resp:
                return json.loads(plain_resp.read().decode())
        except Exception as e2:
            log.error(f"Fallback plain text juga gagal: {e2}")
            return None


def execute_command_async(cmd: str, chat_id: str, token: str):
    """Eksekusi perintah pipeline di thread terpisah agar bot tidak beku."""
    log.info(f"Menjalankan perintah pipeline: {cmd}")

    if cmd == "/semua":
        send_message(token, chat_id, f"Perintah /semua diterima.\nSistem sedang menjalankan pipeline lengkap (Maps, FB Marketplace, IG, TikTok, Matrix).\nMohon tunggu beberapa saat...")
        from run_pipeline import run_all
        try:
            run_all(limit=2, dry_run=False, notify_telegram=True)
            send_message(token, chat_id, f"Eksekusi /semua selesai.\nData terbaru sudah masuk ke spreadsheet:\n{SPREADSHEET_URL}")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /semua: {e}")

    elif cmd == "/prospek":
        send_message(token, chat_id, f"Perintah /prospek diterima.\nMenjalankan scraper Google Maps untuk 9 sektor...")
        from run_pipeline import run_gmaps
        try:
            run_gmaps()
            send_message(token, chat_id, f"Scraper Google Maps selesai.\nData masuk ke tab Radar Prospek:\n{SPREADSHEET_URL}")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /prospek: {e}")

    elif cmd == "/pasar_fb":
        send_message(token, chat_id, f"Perintah /pasar_fb diterima.\nMenjalankan scraping Facebook Marketplace Makassar...")
        from run_pipeline import run_facebook
        try:
            run_facebook()
            send_message(token, chat_id, f"Facebook Marketplace selesai.\nData prospek, harga kompetitor, dan tren diperbarui:\n{SPREADSHEET_URL}")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /pasar_fb: {e}")

    elif cmd == "/kompetitor":
        send_message(token, chat_id, f"Perintah /kompetitor diterima.\nMenganalisis matriks strategi kompetitor percetakan Makassar...")
        from run_pipeline import run_matrix
        try:
            run_matrix()
            send_message(token, chat_id, f"Analisis kompetitor selesai.\nData masuk ke tab Matriks Kompetitor:\n{SPREADSHEET_URL}")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /kompetitor: {e}")

    elif cmd == "/tren":
        send_message(token, chat_id, f"Perintah /tren diterima.\nMemindai tren viral percetakan di TikTok...")
        from run_pipeline import run_tiktok
        try:
            run_tiktok()
            send_message(token, chat_id, f"Pemindaian tren selesai.\nData masuk ke tab Market Signals:\n{SPREADSHEET_URL}")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /tren: {e}")

    elif cmd == "/threads":
        send_message(token, chat_id, f"Perintah /threads diterima.\nMenjalankan scraping Threads Intelligence Makassar...")
        from run_pipeline import run_threads
        try:
            run_threads()
            send_message(token, chat_id, f"Threads Intelligence selesai.\nData masuk ke spreadsheet:\n{SPREADSHEET_URL}")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /threads: {e}")

    elif cmd == "/enrich":
        send_message(token, chat_id, "Perintah /enrich diterima.\nMenjalankan pengayaan nomor WhatsApp dari website calon pelanggan...")
        try:
            from scrapers.web_enricher import enrich_leads_from_websites
            from scrapers.config import PROCESSED_DIR
            leads_files = sorted(PROCESSED_DIR.glob("leads_scored_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if leads_files:
                with open(leads_files[0], "r", encoding="utf-8") as f:
                    leads = json.load(f)
                enriched = enrich_leads_from_websites(leads, limit=10)
                with open(leads_files[0], "w", encoding="utf-8") as f:
                    json.dump(enriched, f, ensure_ascii=False, indent=2)
                from run_pipeline import run_export_csv
                run_export_csv()
                send_message(token, chat_id, f"Pengayaan website selesai.\nFile CSV dan data terbaru telah diperbarui:\n{SPREADSHEET_URL}")
            else:
                send_message(token, chat_id, "Tidak ditemukan file leads untuk diperkaya.")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /enrich: {e}")

    elif cmd == "/dedup":
        send_message(token, chat_id, "Perintah /dedup diterima.\nMemeriksa duplikasi prospek pada database riwayat...")
        try:
            from scrapers.utils import deduplicate_leads, PROCESSED_DIR
            leads_files = sorted(PROCESSED_DIR.glob("leads_scored_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if leads_files:
                with open(leads_files[0], "r", encoding="utf-8") as f:
                    leads = json.load(f)
                clean, dups = deduplicate_leads(leads)
                res_msg = (
                    "<b>RUANG VISUAL — Hasil Deduplikasi Data:</b>\n"
                    f"- File Analisis: <code>{leads_files[0].name}</code>\n"
                    f"- Prospek Bersih/Unik: <b>{len(clean)} bisnis</b>\n"
                    f"- Prospek Duplikat Disaring: <b>{dups} bisnis</b>\n"
                    "Data dipastikan aman dari duplikasi."
                )
                send_message(token, chat_id, res_msg)
            else:
                send_message(token, chat_id, "Tidak ditemukan file riwayat prospek.")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /dedup: {e}")

    elif cmd in ("/kuliner", "/gofood"):
        send_message(token, chat_id, "Perintah /kuliner diterima.\nMenjalankan pencarian merchant GoFood Makassar...")
        from run_pipeline import run_food
        try:
            run_food()
            send_message(token, chat_id, f"Scraper GoFood selesai.\nMerchant kuliner baru masuk ke tab Radar Prospek:\n{SPREADSHEET_URL}")
        except Exception as e:
            send_message(token, chat_id, f"Error saat menjalankan /kuliner: {e}")

    elif cmd == "/bersihkan":
        send_message(token, chat_id, f"Perintah /bersihkan diterima.\nMembersihkan baris data lama di Google Sheets...")
        from run_pipeline import run_clean_sheets
        try:
            run_clean_sheets()
            send_message(token, chat_id, f"Google Sheets berhasil dibersihkan.\nKetiga tab utama kini kosong dan siap diisi:\n{SPREADSHEET_URL}")
        except Exception as e:
            send_message(token, chat_id, f"Error saat membersihkan sheets: {e}")


def run_polling_loop():
    """Loop polling pesan masuk dari Telegram."""
    token = get_env_var("TELEGRAM_BOT_TOKEN")
    if not token:
        log.error("TELEGRAM_BOT_TOKEN belum diset di .env!")
        return

    # Pastikan webhook tidak aktif agar polling dapat menerima update
    try:
        del_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
        urllib.request.urlopen(del_url, timeout=10)
        log.info("Webhook dibersihkan untuk mode polling lokal.")
    except Exception:
        pass

    log.info("=" * 60)
    log.info("RUANG VISUAL — Telegram Bot Local Runner AKTIF")
    log.info("Buka Telegram di HP Anda dan ketik: /menu")
    log.info("=" * 60)

    offset = 0
    while True:
        try:
            get_url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=20"
            req = urllib.request.Request(get_url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            for update in data.get("result", []):
                offset = max(offset, update["update_id"] + 1)
                message = update.get("message")
                if not message or "text" not in message:
                    continue

                chat_id = str(message["chat"]["id"])
                text = message["text"].strip()
                sender = message.get("from", {}).get("first_name", "User")
                log.info(f"Pesan dari {sender} ({chat_id}): {text}")

                cmd = text.split(" ")[0].lower().split("@")[0]

                if cmd in ["/start", "/help", "/menu"]:
                    menu_text = [
                        "<b>RUANG VISUAL — Market Intelligence Pipeline</b>",
                        "Pusat Komando Mobile Makassar Focus",
                        "--------------------------------------------------",
                        "<b>Daftar Perintah:</b>",
                        "<b>/semua</b> : Jalankan seluruh pipeline (Maps, FB, Threads, TikTok, Matrix)",
                        "<b>/prospek</b> : Jalankan pencarian prospek bisnis baru",
                        "<b>/pasar_fb</b> : Jalankan scraping khusus Facebook Marketplace",
                        "<b>/threads</b> : Jalankan pemantauan prospek dan tren Threads",
                        "<b>/kompetitor</b> : Analisis harga dan matriks percetakan kompetitor",
                        "<b>/tren</b> : Pemantauan produk printing viral & sinyal pasar",
                        "<b>/kuliner</b> : Jalankan scraping merchant kuliner GoFood Makassar",
                        "<b>/enrich</b> : Pengayaan nomor WhatsApp dari website calon pelanggan",
                        "<b>/dedup</b> : Periksa duplikasi data pada histori prospek",
                        "<b>/bersihkan</b> : Bersihkan data lama di Google Sheets",
                        "<b>/status</b> : Tampilkan link Google Sheets & status sistem",
                        "--------------------------------------------------",
                        f'<a href="{SPREADSHEET_URL}">Buka Google Spreadsheet</a>',
                    ]
                    send_message(token, chat_id, "\n".join(menu_text))

                elif cmd == "/status":
                    status_text = [
                        "<b>Status Sistem RUANG VISUAL</b>",
                        "Status: Layanan Bot Aktif & Terhubung",
                        "Target: 9 Sektor Usaha Makassar & Radius Workshop",
                        "Database: Google Sheets (3 Tab Resmi)",
                        f'<a href="{SPREADSHEET_URL}">Buka Google Spreadsheet</a>',
                    ]
                    send_message(token, chat_id, "\n".join(status_text))

                elif cmd in ["/semua", "/prospek", "/pasar_fb", "/threads", "/kompetitor", "/tren", "/kuliner", "/gofood", "/enrich", "/dedup", "/bersihkan"]:
                    t = threading.Thread(
                        target=execute_command_async,
                        args=(cmd, chat_id, token),
                        daemon=True,
                    )
                    t.start()

        except KeyboardInterrupt:
            log.info("Bot dihentikan oleh pengguna.")
            break
        except Exception as e:
            log.warning(f"Error pada loop polling: {e}")
            time.sleep(3)


def main():
    run_polling_loop()


if __name__ == "__main__":
    main()
