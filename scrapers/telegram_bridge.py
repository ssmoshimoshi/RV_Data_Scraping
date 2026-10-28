import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import logging
import os
import re
import socket
import sqlite3
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

import threading

load_dotenv()
socket.setdefaulttimeout(30)

# Pastikan path platform-tools Android selalu aktif jika folder ada
ANDROID_TOOLS = "/Users/muhammadfanani/Library/Android/sdk/platform-tools"
if os.path.exists(ANDROID_TOOLS) and ANDROID_TOOLS not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{ANDROID_TOOLS}:{os.environ.get('PATH', '')}"
from scrapers.lead_engine import (
    calculate_lead_score,
    save_lead_to_db,
    get_top_daily_leads,
    link_instagram_to_lead,
    update_lead_field,
    drop_lead,
    get_lead_by_id,
    analyze_post_needs,
    filter_business_accounts
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("telegram_bridge")

DEFAULT_BOT_TOKEN = "8826516320:AAEHnjqrAjJZHFUb9w3X8Mqd80iIoqEP4LA"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or DEFAULT_BOT_TOKEN
TARGET_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-5140963245")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def register_bot_commands() -> bool:
    if not BOT_TOKEN:
        return False
    commands = [
        {"command": "gmaps", "description": "Rayap Google Maps & kirim ke Sheets (misal: /gmaps cafe Makassar 5)"},
        {"command": "scrape", "description": "Rayap profil Instagram (misal: /scrape kopiteori)"},
        {"command": "batch", "description": "Rayap massal beberapa profil sekaligus"},
        {"command": "status", "description": "Cek koneksi perangkat dan status sistem"},
        {"command": "menu", "description": "Buka panel tombol kontrol interaktif RUANG VISUAL"},
        {"command": "db", "description": "Ringkasan data prospek di database SQLite"},
        {"command": "set_ig", "description": "Tautkan Instagram ke prospek (misal: /set_ig LD-0001 kopiteori)"},
        {"command": "edit_lead", "description": "Ubah data prospek (misal: /edit_lead LD-0001 phone 082123456789)"},
        {"command": "drop_lead", "description": "Batalkan prospek (misal: /drop_lead LD-0001 bukan target)"},
        {"command": "help", "description": "Panduan lengkap penggunaan bot"}
    ]
    try:
        data = json.dumps({"commands": commands}).encode("utf-8")
        req = urllib.request.Request(
            f"{API_BASE}/setMyCommands",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            logger.info("Menu perintah Telegram berhasil didaftarkan ke server Telegram.")
            return bool(res.get("ok"))
    except Exception as e:
        logger.warning(f"Gagal mendaftarkan menu perintah bot: {e}")
        return False


def send_telegram_message(
    chat_id: str,
    text: str,
    reply_to_message_id: Optional[int] = None,
    reply_markup: Optional[Dict[str, Any]] = None
) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN") or BOT_TOKEN or DEFAULT_BOT_TOKEN
    target_chat = (chat_id or "").strip() or os.getenv("TELEGRAM_CHAT_ID", "").strip() or TARGET_CHAT_ID or "-5140963245"
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN belum dikonfigurasi di file .env atau secrets.")
        return False

    payload: Dict[str, Any] = {"chat_id": target_chat, "text": text}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("ok"):
                logger.info(f"Pesan Telegram berhasil dikirim ke chat {target_chat}.")
                return True
            else:
                logger.error(f"Telegram API menolak pesan: {res}")
                return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        logger.error(f"Gagal mengirim pesan ke Telegram (HTTP {e.code}): {error_body}")
        return False
    except Exception as e:
        logger.error(f"Gagal mengirim pesan ke Telegram: {e}")
        return False


def answer_callback_query(callback_query_id: str, text: Optional[str] = None) -> bool:
    if not BOT_TOKEN:
        return False
    payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(f"{API_BASE}/answerCallbackQuery", data=data)
        with urllib.request.urlopen(req, timeout=8) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return bool(res.get("ok"))
    except Exception as e:
        logger.warning(f"Gagal menjawab callback query: {e}")
        return False


def get_telegram_updates(offset: Optional[int] = None, timeout: int = 20) -> List[Dict[str, Any]]:
    if not BOT_TOKEN:
        return []

    url = f"{API_BASE}/getUpdates?timeout={timeout}"
    if offset:
        url += f"&offset={offset}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        logger.error(f"Gagal mengambil pembaruan Telegram: {e}")
    return []


def get_control_panel_markup() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "[ Rayap GMaps Makassar (Kafe) ]", "callback_data": "act_scrape_gmaps"},
                {"text": "[ Ringkasan Database ]", "callback_data": "act_db"}
            ],
            [
                {"text": "[ Cek Status Sistem ]", "callback_data": "act_status"},
                {"text": "[ Panduan Perintah ]", "callback_data": "act_help"}
            ]
        ]
    }


def get_persistent_keyboard_markup() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "/gmaps"}, {"text": "/db"}],
            [{"text": "/menu"}, {"text": "/status"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }


def format_profile_report(data: Dict[str, Any]) -> str:
    username = data.get("username", "-")
    full_name = data.get("full_name") or "-"
    category = data.get("business_category") or "Umum"
    followers = data.get("followers_count", 0)
    posts = data.get("posts_count", 0)
    following = data.get("following_count", 0)
    wa = data.get("whatsapp_number") or "-"
    email = data.get("email") or "-"
    address = data.get("address") or "-"
    website = data.get("website_url") or "-"
    bio = data.get("bio") or "-"

    lines = [
        "RUANG VISUAL — LAPORAN HASIL EKSTRAKSI",
        "====================================",
        f"Akun Target     : @{username}",
        f"Nama Bisnis     : {full_name}",
        f"Kategori        : {category}",
        f"Nomor WhatsApp  : {wa}",
        f"Email           : {email}",
        f"Alamat Fisik    : {address}",
        f"Followers       : {followers:,}",
        f"Postingan       : {posts:,}",
        f"Following       : {following:,}",
        f"Website / Bio   : {website}",
        "",
        "Biografi Singkat:",
        bio[:280] + ("..." if len(bio) > 280 else ""),
        "====================================",
        "Status Database : Tersimpan ke data/leads.sqlite"
    ]
    return "\n".join(lines)


def get_system_status() -> str:
    db_path = PROJECT_ROOT / "data" / "leads.sqlite"
    leads_count = 0
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM entities")
            leads_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

    status_lines = [
        "RUANG VISUAL — STATUS SISTEM",
        "====================================",
        "Perangkat Fisik : Xiaomi Redmi Note 14 5G",
        "Status Koneksi  : Terhubung Aktif (USB/ADB)",
        "Motor Ekstraksi : Native Android UIAutomator (0 Token AI)",
        f"Total Leads DB  : {leads_count} entitas tersimpan",
        "Sistem Telegram : Bot Controller Aktif",
        "====================================",
        "Sistem siap menerima perintah perayapan baru."
    ]
    return "\n".join(status_lines)


def get_db_summary() -> str:
    db_path = PROJECT_ROOT / "data" / "leads.sqlite"
    if not db_path.exists():
        return "Database SQLite lokal belum dibuat."

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('leads', 'entities')")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        total_entities = 0
        total_valid_wa = 0
        sector_rows = []
        recent_leads = []
        
        if 'leads' in existing_tables:
            cursor.execute("PRAGMA table_info(leads)")
            lead_cols = [c[1] for c in cursor.fetchall()]
            has_status = 'status' in lead_cols
            status_clause = " WHERE status != 'dropped'" if has_status else ""
            
            cursor.execute(f"SELECT COUNT(*) FROM leads{status_clause}")
            total_leads = cursor.fetchone()[0]
            total_entities += total_leads
            
            wa_col = 'whatsapp' if 'whatsapp' in lead_cols else 'whatsapp_number'
            status_drop_clause = " AND status != 'dropped'" if has_status else ""
            cursor.execute(f"SELECT COUNT(*) FROM leads WHERE {wa_col} IS NOT NULL AND {wa_col} != ''{status_drop_clause}")
            total_valid_wa += cursor.fetchone()[0]
            
            sec_col = 'sector' if 'sector' in lead_cols else ('category' if 'category' in lead_cols else None)
            if sec_col:
                cursor.execute(f"SELECT {sec_col}, COUNT(*) FROM leads{status_clause} GROUP BY {sec_col} ORDER BY COUNT(*) DESC LIMIT 5")
                sector_rows = cursor.fetchall()
            
            order_col = 'created_at' if 'created_at' in lead_cols else ('found_at' if 'found_at' in lead_cols else 'rowid')
            sec_col_expr = sec_col if sec_col else "'general'"
            cursor.execute(f"SELECT business_name, {wa_col}, {sec_col_expr} FROM leads{status_clause} ORDER BY {order_col} DESC LIMIT 5")
            recent_leads = cursor.fetchall()
        
        if 'entities' in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM entities")
            total_entities += cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM entities WHERE is_wa_valid = 1")
            total_valid_wa += cursor.fetchone()[0]
            
            if not sector_rows:
                cursor.execute("SELECT target_sector, COUNT(*) FROM entities GROUP BY target_sector ORDER BY COUNT(*) DESC LIMIT 5")
                sector_rows = cursor.fetchall()
            
            if not recent_leads:
                cursor.execute("SELECT business_name, whatsapp_number, target_sector FROM entities ORDER BY created_at DESC LIMIT 5")
                recent_leads = cursor.fetchall()
        
        conn.close()

        lines = [
            "RUANG VISUAL — RINGKASAN DATABASE PROSPEK",
            "====================================",
            f"Total Entitas Bisnis : {total_entities} entitas",
            f"Nomor WhatsApp Valid : {total_valid_wa} entitas",
            f"Rasio Kontak Valid   : {(total_valid_wa / max(1, total_entities) * 100):.1f}%",
            "",
            "Distribusi Sektor Industri:"
        ]
        for sec, cnt in sector_rows:
            lines.append(f"- {sec or 'Tidak Teridentifikasi'}: {cnt} entitas")

        lines.extend([
            "",
            "5 Prospek Terbaru Tersimpan:"
        ])
        for bname, wnum, sect in recent_leads:
            lines.append(f"- {bname} | WA: {wnum or '-'} | Sektor: {sect or '-'}")

        lines.append("====================================")
        return "\n".join(lines)

    except Exception as e:
        return f"Gagal membaca data database: {e}"


def send_welcome_menu(chat_id: str, reply_to_message_id: Optional[int] = None):
    welcome_text = (
        "RUANG VISUAL — MARKET INTELLIGENCE ENGINE\n"
        "====================================\n"
        "Selamat datang di Pusat Kontrol Perayapan Data RUANG VISUAL.\n"
        "Perangkat: Xiaomi Redmi Note 14 5G (Android 16)\n\n"
        "Anda dapat melakukan perayapan data profil Instagram, tombol kontak "
        "WhatsApp, alamat, dan metrik bisnis secara otomatis langsung dari grup ini.\n\n"
        "Silakan tekan salah satu tombol di bawah untuk tindakan cepat:"
    )
    inline_markup = get_control_panel_markup()
    send_telegram_message(chat_id, welcome_text, reply_to_message_id=reply_to_message_id, reply_markup=inline_markup)

    # Kirim juga keyboard persisten di bawah chat input
    send_telegram_message(
        chat_id,
        "Tombol navigasi cepat telah disematkan di papan tombol chat Anda.",
        reply_markup=get_persistent_keyboard_markup()
    )


def execute_scrape_batch(chat_id: str, target_users: List[str], reply_to_message_id: Optional[int] = None):
    clean_targets = []
    for u in target_users:
        cleaned = u.strip().lstrip("@").strip("<>").strip()
        if cleaned and cleaned not in clean_targets:
            clean_targets.append(cleaned)

    if not clean_targets:
        send_telegram_message(chat_id, "Tidak ada username target yang valid.", reply_to_message_id=reply_to_message_id)
        return

    send_telegram_message(
        chat_id,
        f"Perintah diterima. Memulai perayapan untuk {len(clean_targets)} akun pada perangkat Android...",
        reply_to_message_id=reply_to_message_id
    )

    try:
        from scrapers.android_scraper import (
            ensure_device_ready,
            extract_instagram_profile,
            get_android_device,
            persist_profile_to_db,
            save_raw_output,
        )
        d = get_android_device()
        if not ensure_device_ready(d):
            send_telegram_message(
                chat_id,
                "Gagal: Perangkat Android tidak merespons atau kabel USB terputus.",
                reply_to_message_id=reply_to_message_id
            )
            return

        for idx, user in enumerate(clean_targets, 1):
            logger.info(f"Mengekstrak @{user} atas permintaan grup...")
            profile = extract_instagram_profile(d, user)

            if profile.get("status") == "not_found":
                send_telegram_message(
                    chat_id,
                    f"Akun @{user} tidak ditemukan atau telah dihapus oleh Instagram.",
                    reply_to_message_id=reply_to_message_id
                )
                continue
            elif profile.get("status") == "timeout":
                send_telegram_message(
                    chat_id,
                    f"Batas waktu tercapai saat memuat profil @{user}.",
                    reply_to_message_id=reply_to_message_id
                )
                continue

            save_raw_output(profile, user)
            persist_profile_to_db(profile)

            lead_data = {
                'business_name': profile.get('full_name', user),
                'category': profile.get('category', ''),
                'phone': profile.get('contact_phone_number', ''),
                'website': profile.get('external_url', ''),
                'rating': 0.0,
                'reviews_count': 0,
                'opening_hours': ''
            }
            score = calculate_lead_score(lead_data)
            lead_data['score'] = score
            lead_data['sector'] = profile.get('category', '')
            
            if score >= 70:
                lead_id = save_lead_to_db(lead_data, dry_run=False)
                posts = profile.get('recent_posts', [])
                print_needs = analyze_post_needs(posts)
                
                lead_notification = (
                    f"PROSPEK BARU TERDETEKSI\n"
                    f"========================\n"
                    f"ID: {lead_id}\n"
                    f"Nama: {lead_data['business_name']}\n"
                    f"Kategori: {lead_data['category']}\n"
                    f"Kontak: {lead_data.get('phone', 'Tidak tersedia')}\n"
                    f"Website: {lead_data.get('website', 'Tidak tersedia')}\n"
                    f"Skor: {score}/100\n"
                    f"Status: LAYAK (>= 70)\n\n"
                )
                
                if print_needs:
                    lead_notification += f"Rekomendasi Produk Cetak:\n"
                    for need in print_needs[:5]:
                        lead_notification += f"- {need}\n"
                    lead_notification += f"\n"
                
                lead_notification += f"Gunakan /set_ig {lead_id} {user} untuk menautkan Instagram."
                
                send_telegram_message(chat_id, lead_notification, reply_to_message_id=reply_to_message_id)

            report = format_profile_report(profile)
            send_telegram_message(chat_id, report, reply_to_message_id=reply_to_message_id)

            if idx < len(clean_targets):
                time.sleep(3.5)

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat memproses permintaan Telegram: {e}")
        send_telegram_message(
            chat_id,
            f"Terjadi kesalahan teknis pada sistem perayapan: {e}",
            reply_to_message_id=reply_to_message_id
        )


def run_gmaps_scrape_job(chat_id: str, query: str = "cafe", city: str = "Makassar", limit: int = 5, reply_to_message_id: Optional[int] = None):
    send_telegram_message(
        chat_id,
        f"PERINTAH PERAYAPAN DITERIMA\n"
        f"====================================\n"
        f"Mode          : Radius Konsentris Bertingkat (Titik Hertasning/Panakkukang)\n"
        f"Target        : {limit} tempat usaha\n\n"
        f"Sistem sedang menjalankan perayapan headless Playwright dan sinkronisasi otomatis ke Google Spreadsheet...",
        reply_to_message_id=reply_to_message_id
    )

    try:
        from scrapers.radius_scraper import run_radius_scraper, load_state

        new_leads = run_radius_scraper(limit=limit, dry_run=False)

        for lead in new_leads:
            bname = lead.get("business_name", "")
            wa = lead.get("whatsapp") or lead.get("whatsapp_number") or "-"
            addr = lead.get("address") or lead.get("address_full") or "-"
            rating = lead.get("rating", 0.0)
            revs = lead.get("reviews_count", 0)
            score = lead.get("lead_score", 0)
            tier = lead.get("priority_tier", "Tier D")
            dist = lead.get("distance_km", 0)
            pitch = lead.get("whatsapp_pitch", "")
            wa_link = f"https://wa.me/{wa}" if wa != "-" else ""

            card_text = (
                f"PROSPEK BARU GOOGLE MAPS\n"
                f"====================================\n"
                f"Nama Bisnis : {bname}\n"
                f"Kategori    : {lead.get('category', 'fnb_hospitality')}\n"
                f"WhatsApp    : {wa}\n"
                f"Jarak Titik : {dist} km dari Titik Panakkukang\n"
                f"Alamat      : {addr}\n"
                f"Rating      : {rating} ({revs} ulasan)\n"
                f"Skor Potensi: {score}/100 ({tier})\n"
                f"====================================\n"
                f"Draft Pitch Penawaran:\n{pitch}\n\n"
                f"Tautan WhatsApp Langsung:\n{wa_link}\n\n"
                f"Status: Tersimpan ke SQLite & Google Spreadsheet 'Radar Prospek'"
            )
            send_telegram_message(chat_id, card_text)
            time.sleep(1)

        state = load_state()
        rad = state.get("current_radius_km", 1)
        summary_msg = (
            f"PERAYAPAN GOOGLE MAPS SELESAI\n"
            f"====================================\n"
            f"Mode             : Radius Konsentris Bertingkat\n"
            f"Radius Aktif     : {rad} km dari Titik Panakkukang\n"
            f"Total Prospek    : {len(new_leads)} bisnis baru\n"
            f"Google Sheet     : Berhasil disinkronkan ke 'Radar Prospek'\n"
            f"Database Lokal   : Tersimpan di data/leads.sqlite\n"
            f"===================================="
        )
        send_telegram_message(chat_id, summary_msg)

    except Exception as e:
        logger.error(f"Gagal mengeksekusi perayapan Google Maps: {e}", exc_info=True)
        send_telegram_message(
            chat_id,
            f"Gagal mengeksekusi perayapan Google Maps: {e}",
            reply_to_message_id=reply_to_message_id
        )


def handle_callback_query(cb_query: Dict[str, Any]):
    query_id = cb_query.get("id", "")
    data = cb_query.get("data", "")
    message = cb_query.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", TARGET_CHAT_ID))
    message_id = message.get("message_id")

    logger.info(f"Menangani callback_query: '{data}' dari chat {chat_id}")
    answer_callback_query(query_id, text="Memproses perintah...")

    if data == "act_scrape_gmaps":
        threading.Thread(
            target=run_gmaps_scrape_job,
            args=(chat_id, "cafe", "Makassar", 5, message_id),
            daemon=True
        ).start()

    elif data == "act_status":
        status_text = get_system_status()
        send_telegram_message(chat_id, status_text, reply_to_message_id=message_id)

    elif data == "act_db":
        db_text = get_db_summary()
        send_telegram_message(chat_id, db_text, reply_to_message_id=message_id)

    elif data == "act_help":
        help_msg = (
            "PANDUAN PENGGUNAAN BOT RUANG VISUAL\n"
            "====================================\n"
            "Format Perintah Teks:\n"
            "1. /gmaps [kata_kunci] [kota] [limit]\n"
            "   Contoh: /gmaps cafe Makassar 5\n"
            "   Contoh: /gmaps bakery Makassar 5\n"
            "   (Data otomatis tersimpan ke SQLite & Google Spreadsheet)\n\n"
            "2. /scrape <username>\n"
            "   Contoh: /scrape janjijiwa.id\n\n"
            "3. /batch <akun1, akun2, ...>\n"
            "   Contoh: /batch kopiteori, sofikopi.store\n\n"
            "4. /status\n"
            "   Cek kesiapan fisik ponsel dan koneksi ADB.\n\n"
            "5. /db\n"
            "   Cek ringkasan database dan prospek tersimpan.\n\n"
            "6. /menu\n"
            "   Buka kembali panel kontrol interaktif berpenampilan RUANG VISUAL."
        )
        send_telegram_message(chat_id, help_msg, reply_to_message_id=message_id)


def handle_incoming_command(text: str, chat_id: str, message_id: int):
    clean_text = text.strip()
    logger.info(f"Menerima pesan dari chat {chat_id}: '{clean_text}'")

    if clean_text in ["/start", "/menu", "/start@RuangVisualBot", "/menu@RuangVisualBot"]:
        send_welcome_menu(chat_id, reply_to_message_id=message_id)
        return

    if clean_text in ["/help", "/help@RuangVisualBot"]:
        help_msg = (
            "PANDUAN PERINTAH BOT SCRAPING RUANG VISUAL\n"
            "====================================\n"
            "1. /gmaps [kata_kunci] [kota] [limit]\n"
            "   Merayap tempat Google Maps, kualifikasi prospek, dan otomatis sync ke Google Spreadsheet.\n"
            "   Contoh: /gmaps cafe Makassar 5\n"
            "   Contoh: /gmaps\n\n"
            "2. /scrape <username>\n"
            "   Merayap satu profil Instagram.\n"
            "   Contoh: /scrape kopiteori\n\n"
            "3. /batch <akun1, akun2, ...>\n"
            "   Merayap beberapa profil secara berurutan.\n"
            "   Contoh: /batch kopiteori, sofikopi.store\n\n"
            "4. /status\n"
            "   Melihat status sistem dan perangkat fisik.\n\n"
            "5. /db\n"
            "   Melihat total data prospek di database SQLite.\n\n"
            "6. /set_ig <LEAD_ID> <username>\n"
            "   Menautkan Instagram ke prospek.\n"
            "   Contoh: /set_ig LD-0001 kopiteori\n\n"
            "7. /edit_lead <LEAD_ID> <field> <nilai>\n"
            "   Memperbarui data prospek.\n"
            "   Contoh: /edit_lead LD-0001 phone 082123456789\n\n"
            "8. /drop_lead <LEAD_ID> <alasan>\n"
            "   Membatalkan prospek.\n"
            "   Contoh: /drop_lead LD-0001 bukan target\n\n"
            "9. /queue\n"
            "   Melihat antrean akun yang akan dirayap di ponsel Android.\n\n"
            "10. /run_phone\n"
            "   Mengeksekusi antrean perayapan profil Instagram di perangkat Android fisik.\n\n"
            "11. /menu\n"
            "   Membuka panel tombol kontrol interaktif."
        )
        send_telegram_message(chat_id, help_msg, reply_to_message_id=message_id)
        return

    if clean_text.startswith("/gmaps"):
        parts = clean_text.split()
        query = "cafe"
        city = "Makassar"
        limit = 5
        if len(parts) >= 2 and parts[1]:
            query = parts[1]
        if len(parts) >= 3 and parts[2]:
            city = parts[2]
        if len(parts) >= 4 and parts[3]:
            try:
                limit = int(parts[3])
            except ValueError:
                limit = 5

        threading.Thread(
            target=run_gmaps_scrape_job,
            args=(chat_id, query, city, limit, message_id),
            daemon=True
        ).start()
        return

    if clean_text in ["/status", "/status@RuangVisualBot"]:
        status_msg = get_system_status()
        send_telegram_message(chat_id, status_msg, reply_to_message_id=message_id)
        return

    if clean_text in ["/db", "/db@RuangVisualBot"]:
        db_msg = get_db_summary()
        send_telegram_message(chat_id, db_msg, reply_to_message_id=message_id)
        return

    if clean_text in ["/queue", "/queue@RuangVisualBot", "/antrean"]:
        from scrapers.phone_queue import load_queue
        q_data = load_queue()
        items = q_data.get("queue", [])
        pending = [it for it in items if it.get("status") == "pending"]
        processing = [it for it in items if it.get("status") == "processing"]
        lines = [
            "STATUS ANTREAN PERAYAPAN ANDROID",
            "================================",
            f"Total Antrean : {len(items)}",
            f"Pending       : {len(pending)}",
            f"Sedang Jalan  : {len(processing)}",
            ""
        ]
        if pending:
            lines.append("Daftar Akun Pending:")
            for idx, p in enumerate(pending[:10], 1):
                lines.append(f"{idx}. @{p.get('handle')} - {p.get('business_name')} ({p.get('lead_id')})")
        else:
            lines.append("Tidak ada akun dalam antrean pending.")
        lines.append("\nKetik /run_phone untuk mengeksekusi antrean di ponsel fisik Android.")
        send_telegram_message(chat_id, "\n".join(lines), reply_to_message_id=message_id)
        return

    if clean_text in ["/run_phone", "/run_phone@RuangVisualBot", "/jalankan_ponsel"]:
        from scrapers.phone_queue import get_pending_items, update_item_status
        pending = get_pending_items()
        if not pending:
            send_telegram_message(chat_id, "Tidak ada akun dalam antrean pending saat ini.", reply_to_message_id=message_id)
            return

        send_telegram_message(
            chat_id,
            f"Memulai perayapan antrean untuk {len(pending)} akun pada perangkat Android...",
            reply_to_message_id=message_id
        )

        def _bg_process_queue():
            try:
                from scrapers.android_scraper import (
                    get_android_device,
                    ensure_device_ready,
                    extract_instagram_profile,
                    persist_profile_to_db,
                    save_raw_output
                )
                d = get_android_device()
                if not ensure_device_ready(d):
                    send_telegram_message(chat_id, "Gagal: Perangkat Android tidak merespons atau kabel USB terputus.")
                    return

                for it in pending:
                    q_id = it["id"]
                    uname = it["handle"]
                    bname = it.get("business_name") or uname
                    update_item_status(q_id, "processing")

                    profile = extract_instagram_profile(d, uname)
                    if profile.get("status") in ("not_found", "timeout"):
                        update_item_status(q_id, "failed", profile.get("status"))
                        send_telegram_message(chat_id, f"Gagal merayap @{uname}: status {profile.get('status')}")
                    else:
                        save_raw_output(profile, uname)
                        persist_profile_to_db(profile, entity_id=it.get("lead_id"))
                        update_item_status(q_id, "completed")
                        send_telegram_message(
                            chat_id,
                            f"[BERHASIL DIRAYAP]\n"
                            f"Usaha: {bname}\n"
                            f"Akun: @{uname}\n"
                            f"WhatsApp: {profile.get('contact_phone_number') or '-'}\n"
                            f"Followers: {profile.get('followers_count') or 0}"
                        )
                send_telegram_message(chat_id, f"Seluruh antrean perayapan ponsel ({len(pending)} akun) telah selesai diproses.")
            except Exception as e:
                logger.error(f"Error proses antrean ponsel: {e}")
                send_telegram_message(chat_id, f"Terjadi kesalahan saat memproses antrean ponsel: {e}")

        threading.Thread(target=_bg_process_queue, daemon=True).start()
        return

    if clean_text.startswith("/set_ig"):
        parts = clean_text.split()
        if len(parts) >= 3:
            lead_id = parts[1].strip().upper()
            ig_handle = parts[2].strip().lstrip("@")
            if link_instagram_to_lead(lead_id, ig_handle):
                send_telegram_message(
                    chat_id,
                    f"Berhasil menautkan Instagram @{ig_handle} ke {lead_id}. Perayapan profil akan dimulai.",
                    reply_to_message_id=message_id
                )
                target_users = [ig_handle]
                execute_scrape_batch(chat_id, target_users, reply_to_message_id=message_id)
            else:
                send_telegram_message(
                    chat_id,
                    f"Gagal menautkan. Pastikan {lead_id} ada di database.",
                    reply_to_message_id=message_id
                )
        else:
            send_telegram_message(
                chat_id,
                "Format: /set_ig <LEAD_ID> <username>\nContoh: /set_ig LD-0001 kopiteori",
                reply_to_message_id=message_id
            )
        return

    if clean_text.startswith("/edit_lead"):
        parts = clean_text.split(maxsplit=3)
        if len(parts) >= 4:
            lead_id = parts[1].strip().upper()
            field = parts[2].strip().lower()
            value = parts[3].strip()
            if update_lead_field(lead_id, field, value):
                send_telegram_message(
                    chat_id,
                    f"Berhasil memperbarui {field} untuk {lead_id}.",
                    reply_to_message_id=message_id
                )
            else:
                send_telegram_message(
                    chat_id,
                    f"Gagal memperbarui. Periksa {lead_id} dan field (business_name, phone, whatsapp, address, website).",
                    reply_to_message_id=message_id
                )
        else:
            send_telegram_message(
                chat_id,
                "Format: /edit_lead <LEAD_ID> <field> <nilai>\nContoh: /edit_lead LD-0001 phone 082123456789",
                reply_to_message_id=message_id
            )
        return

    if clean_text.startswith("/drop_lead"):
        parts = clean_text.split(maxsplit=2)
        if len(parts) >= 3:
            lead_id = parts[1].strip().upper()
            reason = parts[2].strip()
            if drop_lead(lead_id, reason):
                send_telegram_message(
                    chat_id,
                    f"{lead_id} telah dibatalkan. Alasan: {reason}",
                    reply_to_message_id=message_id
                )
            else:
                send_telegram_message(
                    chat_id,
                    f"Gagal membatalkan {lead_id}. Pastikan ID valid.",
                    reply_to_message_id=message_id
                )
        else:
            send_telegram_message(
                chat_id,
                "Format: /drop_lead <LEAD_ID> <alasan>\nContoh: /drop_lead LD-0001 bukan target pasar",
                reply_to_message_id=message_id
            )
        return

    target_users = []
    if clean_text.startswith("/scrape"):
        parts = clean_text.split()
        if len(parts) >= 2:
            target_name = parts[1].strip().lstrip("@").strip("<>").strip()
            if target_name:
                target_users.append(target_name)
        else:
            send_telegram_message(
                chat_id,
                "Format tidak lengkap. Gunakan: /scrape <username>",
                reply_to_message_id=message_id
            )
            return

    elif clean_text.startswith("/batch"):
        content = clean_text[len("/batch"):].strip()
        if content:
            raw_items = [u.strip().lstrip("@").strip("<>").strip() for u in content.split(",") if u.strip()]
            target_users.extend([u for u in raw_items if u])
        else:
            send_telegram_message(
                chat_id,
                "Format tidak lengkap. Gunakan: /batch <akun1, akun2, ...>",
                reply_to_message_id=message_id
            )
            return

    elif clean_text.startswith("@") and len(clean_text.split()) == 1:
        target_users.append(clean_text.lstrip("@").strip("<>").strip())

    else:
        return

    if target_users:
        execute_scrape_batch(chat_id, target_users, reply_to_message_id=message_id)


def start_telegram_bridge(run_once: bool = False):
    logger.info("Memulai Telegram Bridge untuk RUANG VISUAL...")
    logger.info(f"Target Grup Chat ID: {TARGET_CHAT_ID}")

    register_bot_commands()

    offset = None
    initial_updates = get_telegram_updates(timeout=1)
    if initial_updates:
        offset = initial_updates[-1]["update_id"] + 1
        logger.info(f"Membersihkan {len(initial_updates)} pesan backlog lama.")

    # Kirim pesan menu pembuka ke grup jika belum pernah
    send_welcome_menu(TARGET_CHAT_ID)
    logger.info("Bot Telegram aktif dan siap mendengarkan perintah di grup...")

    while True:
        try:
            updates = get_telegram_updates(offset=offset, timeout=20)
            for upd in updates:
                offset = upd["update_id"] + 1

                # Tangani tombol inline (callback_query)
                cb_query = upd.get("callback_query")
                if cb_query:
                    handle_callback_query(cb_query)
                    continue

                # Tangani pesan teks masuk
                msg = upd.get("message")
                if not msg:
                    continue

                chat = msg.get("chat", {})
                chat_id = str(chat.get("id"))
                text = msg.get("text", "")
                message_id = msg.get("message_id")

                if text:
                    handle_incoming_command(text, chat_id, message_id)

            if run_once:
                break

        except KeyboardInterrupt:
            logger.info("Telegram bridge dihentikan oleh pengguna.")
            break
        except Exception as e:
            logger.error(f"Kesalahan pada loop utama: {e}")
            time.sleep(3)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RUANG VISUAL — Telegram Bot Controller Bridge")
    parser.add_argument("--once", action="store_true", help="Jalankan sekali periksa pesan dan keluar")
    args = parser.parse_args()
    start_telegram_bridge(run_once=args.once)
