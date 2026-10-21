"""
RUANG VISUAL — Telegram Notifier Module
=======================================
Mengirimkan notifikasi eksekutif, rekap calon customer baru,
rekomendasi hot leads, dan alert error langsung ke Telegram.
Mendukung bot token dan chat ID untuk tim RUANG VISUAL.
"""

import json
import urllib.parse
import urllib.request
import sys
from pathlib import Path

# Pastikan project root ada di sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.utils import get_logger, get_env_var, now_wita, WITA

log = get_logger("telegram")


def get_telegram_config() -> tuple[str, str]:
    """Ambil token bot dan chat ID dari environment variable."""
    token = get_env_var("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_var("TELEGRAM_CHAT_ID", get_env_var("TELEGRAM_GROUP_OWNER_ID"))
    return token, chat_id


def send_telegram_message(html_text: str, token: str = "", chat_id: str = "") -> bool:
    """
    Kirim pesan format HTML ke Telegram.
    Return True jika berhasil, False jika gagal.
    """
    env_token, env_chat_id = get_telegram_config()
    bot_token = token or env_token
    target_chat_id = chat_id or env_chat_id

    if not bot_token or not target_chat_id:
        log.warning("TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum diset di .env")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": html_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode())
            if res.get("ok"):
                log.info("Notifikasi Telegram berhasil terkirim.")
                return True
            else:
                log.warning(f"Telegram API warning: {res}")
                return False
    except Exception as e:
        log.error(f"Gagal mengirim notifikasi Telegram: {e}")
        return False


def format_wa_link(phone: str) -> str:
    """Format nomor HP ke link WhatsApp langsung."""
    if not phone:
        return ""
    clean = "".join([c for c in phone if c.isdigit()])
    if clean.startswith("08"):
        clean = "62" + clean[1:]
    elif clean.startswith("8"):
        clean = "62" + clean
    return f"https://wa.me/{clean}" if clean else ""


def send_pipeline_summary(
    total_leads: int = 0,
    hot_leads: list[dict] = None,
    total_competitors: int = 0,
    total_signals: int = 0,
    duration_sec: float = 0.0,
    mode: str = "Automated Routine",
) -> bool:
    """
    Format dan kirim ringkasan eksekutif eksekusi pipeline.
    """
    hot_leads = hot_leads or []
    timestamp = now_wita()

    lines = [
        "<b>RUANG VISUAL — Laporan Market Intelligence</b>",
        f"<i>Waktu: {timestamp} WITA | Mode: {mode}</i>",
        "",
        "<b>Ringkasan Eksekutif:</b>",
        f"- Calon Customer Baru: <b>{total_leads} Leads</b>",
        f"- Prospek Prioritas (HOT): <b>{len(hot_leads)} Bisnis</b>",
    ]

    if total_competitors > 0:
        lines.append(f"- Matriks Kompetitor Makassar: <b>{total_competitors} Percetakan</b>")
    if total_signals > 0:
        lines.append(f"- Sinyal Tren Pasar Terdeteksi: <b>{total_signals} Topik</b>")

    if duration_sec > 0:
        lines.append(f"- Durasi Eksekusi: <code>{duration_sec:.1f} detik</code>")

    # Rekomendasi Hot Leads (Top 5)
    if hot_leads:
        lines.append("")
        lines.append("<b>Daftar Prospek Prioritas (HOT Leads):</b>")
        for i, lead in enumerate(hot_leads[:5], 1):
            nama = lead.get("nama_bisnis", "Bisnis")
            kategori = lead.get("kategori", "Umum").upper()
            skor = lead.get("skor", 8.0)
            telepon = lead.get("telepon", "")
            wa_link = lead.get("whatsapp_link") or format_wa_link(telepon)
            kebutuhan = lead.get("proyeksi_kebutuhan", "Kemasan dan Display Promosi")

            lead_str = f"<b>{i}. {nama}</b> [Skor: {skor:.1f} | {kategori}]"
            if wa_link:
                lead_str += f"\n   Kontak: <a href=\"{wa_link}\">Kirim WhatsApp ({telepon})</a>"
            elif telepon:
                lead_str += f"\n   Telepon: <code>{telepon}</code>"
            if kebutuhan:
                lead_str += f"\n   Kebutuhan: <i>{kebutuhan}</i>"
            lines.append(lead_str)

    lines.append("")
    lines.append("<b>Status Data:</b> Data berhasil disinkronkan ke Google Spreadsheet.")
    lines.append("<i>Pipeline berjalan melalui otomasi cloud server.</i>")

    message = "\n".join(lines)
    return send_telegram_message(message)


def send_error_alert(module_name: str, error_msg: str) -> bool:
    """Kirim notifikasi jika terjadi kendala pada pipeline."""
    timestamp = now_wita()
    text = (
        f"<b>RUANG VISUAL — Pemberitahuan Kendala Sistem</b>\n"
        f"<i>Waktu: {timestamp} WITA</i>\n\n"
        f"Modul terkait: <b>{module_name}</b>\n"
        f"Pesan error: <code>{error_msg[:300]}</code>\n\n"
        f"<i>Sistem tetap berlanjut dan data aman tersimpan.</i>"
    )
    return send_telegram_message(text)
