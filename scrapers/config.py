import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Konfigurasi Wilayah Operasional RUANG VISUAL
CITY_DEFAULT = "Makassar"
LAT_ORIGIN = -5.15759432245317
LON_ORIGIN = 119.43530577903459

DEFAULT_RADIUS_KM = 1
MAX_RADIUS_KM = 15

# Sektor Target dan Kata Kunci Pencarian Google Maps
SECTOR_QUERIES = {
    "fnb_hospitality": ["kafe", "kedai kopi", "roastery", "restoran", "bakery", "toko kue", "katering"],
    "retail_apparel": ["butik pakaian", "hijab store", "distro clothing", "toko baju"],
    "beauty_skincare": ["klinik kecantikan", "klinik estetika", "dokter gigi", "salon", "spa"],
    "corporate_legal": ["notaris ppat", "kantor hukum", "advokat", "konsultan hukum"],
    "event_wedding": ["wedding organizer", "event planner", "dekorasi pesta", "wedding decoration"]
}

# Integrasi Google Sheets Hermes
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1mDx0aQcz95iPN6KwdmRgb2RE2xVNIhAgiuoq96k6dAU").strip()
SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
DEFAULT_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwHCyHBZ1qEl8Mz4Fv9ClVtUIu6vDRuSvRZxFe8YmdYRRPgkoEdFTOSGC7nX9ymgvw/exec"
WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip() or DEFAULT_WEBHOOK_URL

# Jalur Berkas Data
DATA_DIR = PROJECT_ROOT / "data"
LEADS_DB = DATA_DIR / "leads.sqlite"
STATE_FILE = DATA_DIR / "search_state.json"
PHONE_QUEUE_FILE = DATA_DIR / "phone_queue.json"
CATALOG_FILE = DATA_DIR / "catalog" / "ruang_visual_catalog.json"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"
