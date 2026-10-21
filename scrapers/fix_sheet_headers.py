"""
RUANG VISUAL - Fix Sheet Headers Utility
=========================================
Skrip utilitas mandiri untuk memperbaiki header Google Sheets tab "Radar Prospek"
menjadi 14 kolom standar sesuai AGENTS.md.

Tugas:
1. Mengosongkan data lama yang tata letak kolomnya bergeser
2. Menulis 14 header resmi baru pada baris 1

Cara pakai:
    python3 scrapers/fix_sheet_headers.py
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import urllib.request
from scrapers.utils import get_env_var, get_logger

log = get_logger("fix-headers")

HEADERS_RADAR_PROSPEK_14_KOLOM = [
    "Nama Bisnis",
    "Kategori", 
    "Sumber Platform",
    "Skor",
    "Status",
    "No. WhatsApp",
    "Link WA",
    "Proyeksi Kebutuhan Cetak",
    "Pemicu Kebutuhan & Konteks",
    "Alamat",
    "Rating & Ulasan",
    "Website",
    "Link Sumber Asli",
    "Tanggal"
]


def clear_and_rewrite_headers():
    """
    Kirim payload ke Google Apps Script Webhook untuk:
    1. Clear data lama di tab "Radar Prospek"
    2. Tulis header 14 kolom baru di baris 1
    """
    webhook_url = get_env_var("GOOGLE_SHEET_WEBHOOK_URL")
    if not webhook_url:
        log.error("GOOGLE_SHEET_WEBHOOK_URL tidak ditemukan di .env")
        return False
    
    log.info("Mengirim permintaan clear + rewrite header ke Google Sheets...")
    
    payload = {
        "sheet_name": "Radar Prospek",
        "action": "replace_all",
        "headers": HEADERS_RADAR_PROSPEK_14_KOLOM,
        "rows": []
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_text = resp.read().decode("utf-8")
            log.info(f"Response dari webhook: {response_text}")
            log.info("Header 14 kolom berhasil ditulis ulang di tab 'Radar Prospek'")
            return True
            
    except Exception as e:
        log.error(f"Gagal mengirim payload ke webhook: {e}")
        return False


def main():
    log.info("=== RUANG VISUAL - Fix Sheet Headers ===")
    log.info(f"Target: Tab 'Radar Prospek' -> 14 kolom standar")
    log.info(f"Header: {', '.join(HEADERS_RADAR_PROSPEK_14_KOLOM[:3])}... (14 total)")
    
    success = clear_and_rewrite_headers()
    
    if success:
        log.info("\n=== SELESAI ===")
        log.info("Tab 'Radar Prospek' sudah siap menerima data dengan format 14 kolom.")
        log.info("Lanjutkan dengan eksekusi scraping live: python3 scrapers/food_delivery_scraper.py --limit 10")
    else:
        log.error("\n=== GAGAL ===")
        log.error("Periksa GOOGLE_SHEET_WEBHOOK_URL di .env dan koneksi internet.")
        sys.exit(1)


if __name__ == "__main__":
    main()
