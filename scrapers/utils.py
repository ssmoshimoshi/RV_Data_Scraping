"""
RUANG VISUAL — Shared Utilities
=================================
Helper functions: rate limiting, logging, data saving, Google Sheets integration.
Referensi: intelligence_pipeline_prd.md §4 Arsitektur Sistem
"""

import json
import time
import random
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from scrapers.config import RAW_DIR, PROCESSED_DIR

# ─── Timezone ─────────────────────────────────────────────────────────────────
WITA = timezone(timedelta(hours=8))  # Makassar = WITA (UTC+8)


# ─── Logging Setup ────────────────────────────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """Buat logger dengan format standar pipeline."""
    logger = logging.getLogger(f"rv-pipeline.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            datefmt="%H:%M:%S"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ─── Rate Limiting ────────────────────────────────────────────────────────────
def rate_limit(delay_range: tuple[int, int]):
    """Tunggu random delay antara min dan max detik. WAJIB dipanggil antar request."""
    delay = random.uniform(delay_range[0], delay_range[1])
    time.sleep(delay)
    return delay


# ─── Lead Deduplication Engine ───────────────────────────────────────────────
def normalize_business_name(name: str) -> str:
    """
    Normalize business name for deduplication.
    Remove PT, CV, UD prefixes and convert to lowercase.
    """
    if not name:
        return ""
    
    name_lower = name.lower().strip()
    
    # Remove common business entity prefixes
    prefixes = ["pt ", "pt. ", "cv ", "cv. ", "ud ", "ud. ", "toko ", "warung ", "resto "]
    for prefix in prefixes:
        if name_lower.startswith(prefix):
            name_lower = name_lower[len(prefix):].strip()
    
    return name_lower


def deduplicate_leads(new_leads: list, history_file_pattern: str = "data/processed/leads_scored_*.json") -> tuple[list, int]:
    """
    Remove duplicate leads based on existing history files.
    
    Args:
        new_leads: List of new lead dictionaries to check
        history_file_pattern: Glob pattern for historical lead files
    
    Returns:
        Tuple of (clean_leads, duplicate_count)
    """
    logger = get_logger("deduplicator")
    
    # Collect existing leads from history
    existing_phones = set()
    existing_names = set()
    
    history_files = sorted(PROCESSED_DIR.glob("leads_scored_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    
    total_historical_leads = 0
    for history_file in history_files:
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                historical_leads = json.load(f)
                total_historical_leads += len(historical_leads)
                
                for lead in historical_leads:
                    # Extract and normalize phone numbers
                    phone = lead.get('no_whatsapp', '') or lead.get('telepon', '')
                    if phone:
                        # Normalize to 628xxx format
                        phone_clean = ''.join(c for c in str(phone) if c.isdigit())
                        if phone_clean.startswith('08'):
                            phone_clean = '62' + phone_clean[1:]
                        elif phone_clean.startswith('8'):
                            phone_clean = '62' + phone_clean
                        
                        if phone_clean and len(phone_clean) >= 10:
                            existing_phones.add(phone_clean)
                    
                    # Extract and normalize business names
                    name = lead.get('nama_bisnis', '')
                    if name:
                        normalized_name = normalize_business_name(name)
                        if normalized_name:
                            existing_names.add(normalized_name)
        
        except Exception as e:
            logger.warning(f"Could not read history file {history_file.name}: {e}")
    
    logger.info(f"Loaded {total_historical_leads} historical leads from {len(history_files)} files")
    logger.info(f"Found {len(existing_phones)} unique phone numbers and {len(existing_names)} unique business names")
    
    # Filter new leads
    clean_leads = []
    duplicate_count = 0
    
    for lead in new_leads:
        is_duplicate = False
        
        # Check phone number
        phone = lead.get('no_whatsapp', '') or lead.get('telepon', '')
        if phone:
            phone_clean = ''.join(c for c in str(phone) if c.isdigit())
            if phone_clean.startswith('08'):
                phone_clean = '62' + phone_clean[1:]
            elif phone_clean.startswith('8'):
                phone_clean = '62' + phone_clean
            
            if phone_clean in existing_phones:
                is_duplicate = True
                logger.debug(f"Duplicate phone: {lead.get('nama_bisnis', 'Unknown')} ({phone_clean})")
        
        # Check business name if phone not duplicate
        if not is_duplicate:
            name = lead.get('nama_bisnis', '')
            if name:
                normalized_name = normalize_business_name(name)
                if normalized_name in existing_names:
                    is_duplicate = True
                    logger.debug(f"Duplicate name: {name}")
        
        if is_duplicate:
            duplicate_count += 1
        else:
            clean_leads.append(lead)
            
            # Add to existing sets to prevent intra-batch duplicates
            if phone:
                phone_clean = ''.join(c for c in str(phone) if c.isdigit())
                if phone_clean.startswith('08'):
                    phone_clean = '62' + phone_clean[1:]
                elif phone_clean.startswith('8'):
                    phone_clean = '62' + phone_clean
                if phone_clean and len(phone_clean) >= 10:
                    existing_phones.add(phone_clean)
            
            name = lead.get('nama_bisnis', '')
            if name:
                normalized_name = normalize_business_name(name)
                if normalized_name:
                    existing_names.add(normalized_name)
    
    logger.info(f"Deduplication complete: {len(clean_leads)} new leads, {duplicate_count} duplicates filtered")
    
    return clean_leads, duplicate_count


# ─── Browser Helper ──────────────────────────────────────────────────────────
def launch_stealth_browser(p, headless: bool = True):
    """
    Launch browser yang kompatibel di semua environment:
    1. Mencoba channel='chrome' (optimal untuk dev lokal di macOS).
    2. Fallback ke standard chromium Playwright (optimal untuk Linux / GitHub Actions runner).
    """
    try:
        return p.chromium.launch(channel="chrome", headless=headless)
    except Exception:
        return p.chromium.launch(headless=headless)


# ─── Timestamp ────────────────────────────────────────────────────────────────
def now_wita() -> str:
    """Return current datetime string in WITA timezone."""
    return datetime.now(WITA).strftime("%Y-%m-%d %H:%M:%S")


def today_wita() -> str:
    """Return current date string in WITA timezone."""
    return datetime.now(WITA).strftime("%Y-%m-%d")


# ─── Data Persistence ────────────────────────────────────────────────────────
def save_raw_json(data: list[dict], module_name: str, query: str = "") -> Path:
    """
    Simpan raw scraping results ke file JSON di data/raw/.
    Returns path ke file yang disimpan.
    """
    timestamp = datetime.now(WITA).strftime("%Y%m%d_%H%M%S")
    safe_query = query.replace(" ", "_").replace("/", "-")[:50] if query else "all"
    filename = f"{module_name}_{safe_query}_{timestamp}.json"
    filepath = RAW_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def load_raw_json(filepath: Path) -> list[dict]:
    """Load raw JSON data dari file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Google Sheets Helper ────────────────────────────────────────────────────
# ─── Google Sheets Helper ────────────────────────────────────────────────────
def get_env_var(key: str, default: str = "") -> str:
    """Ambil env var dari root .env atau hermes-mcp-server/.env."""
    import os
    try:
        from dotenv import load_dotenv
        root_env = Path(__file__).parent.parent / ".env"
        hermes_env = Path(__file__).parent.parent / "hermes-mcp-server" / ".env"
        if root_env.exists():
            load_dotenv(root_env)
        if hermes_env.exists():
            load_dotenv(hermes_env)
    except ImportError:
        # Fallback manual jika dijalankan di luar venv tanpa modul python-dotenv
        for env_file in [Path(__file__).parent.parent / ".env", Path(__file__).parent.parent / "hermes-mcp-server" / ".env"]:
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        sline = line.strip()
                        if sline and not sline.startswith("#") and "=" in sline:
                            k, v = sline.split("=", 1)
                            if k.strip() not in os.environ:
                                os.environ[k.strip()] = v.strip().strip("'\"")

    return os.getenv(key, default).strip()


def build_sheets_service():
    """
    Buat Google Sheets API service menggunakan Service Account.
    """
    import os
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa_file = get_env_var("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service-account.json")
    if not Path(sa_file).is_absolute():
        # Coba root credentials/ lalu hermes credentials/
        if (Path(__file__).parent.parent / sa_file).exists():
            sa_file = str(Path(__file__).parent.parent / sa_file)
        else:
            sa_file = str(Path(__file__).parent.parent / "hermes-mcp-server" / sa_file)

    if not Path(sa_file).exists():
        raise FileNotFoundError(
            f"Service Account file tidak ditemukan di '{sa_file}'."
        )

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = service_account.Credentials.from_service_account_file(sa_file, scopes=scopes)
    return build("sheets", "v4", credentials=credentials)


def get_spreadsheet_id() -> str:
    """Ambil SPREADSHEET_ID dari .env."""
    sid = get_env_var("SPREADSHEET_ID")
    if not sid or sid == "your-spreadsheet-id-here":
        raise ValueError("SPREADSHEET_ID belum diisi di file .env!")
    return sid


def append_rows_to_sheet(sheet_name: str, rows: list[list[str]], action: str = "append", headers: list[str] = None):
    """
    Append multiple rows ke Google Sheet.
    Mendukung 2 metode:
    1. Google Apps Script Webhook (Instant tanpa GCP Console) jika GOOGLE_SHEET_WEBHOOK_URL terisi
    2. Google Sheets API v4 (Service Account) jika Service Account JSON terpasang
    """
    logger = get_logger("sheets")
    webhook_url = get_env_var("GOOGLE_SHEET_WEBHOOK_URL")

    # METODE 1: Webhook (Google Apps Script)
    if webhook_url:
        import urllib.request
        body_dict = {"sheet_name": sheet_name, "rows": rows, "action": action}
        if headers:
            body_dict["headers"] = headers
        payload = json.dumps(body_dict).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            logger.info(f"{len(rows)} baris terkirim ke Google Sheets ('{sheet_name}') via Webhook [Action: {action}]")
            return len(rows)

    # METODE 2: Official Google Sheets API v4
    service = build_sheets_service()
    spreadsheet_id = get_spreadsheet_id()

    body = {"values": rows}
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    updated = result.get("updates", {}).get("updatedRows", 0)
    logger.info(f"{updated} baris ditambahkan ke '{sheet_name}'")
    return updated


def read_sheet(sheet_name: str, range_notation: str = "") -> list[list[str]]:
    """Baca data dari Google Sheet."""
    webhook_url = get_env_var("GOOGLE_SHEET_WEBHOOK_URL")
    if webhook_url:
        # Jika menggunakan webhook, pembacaan deduplikasi dilakukan dari data/processed lokal
        return []

    service = build_sheets_service()
    spreadsheet_id = get_spreadsheet_id()
    range_str = f"{sheet_name}!{range_notation}" if range_notation else sheet_name

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_str)
        .execute()
    )
    return result.get("values", [])


# ─── Deduplication ────────────────────────────────────────────────────────────
def get_existing_names(sheet_name: str, column_index: int = 0) -> set[str]:
    """
    Ambil semua nama yang sudah ada di sheet untuk mencegah duplikasi.
    column_index: 0 = kolom A (nama bisnis)
    """
    try:
        rows = read_sheet(sheet_name)
        if len(rows) <= 1:  # Hanya header
            return set()
        return {row[column_index].strip().lower() for row in rows[1:] if len(row) > column_index}
    except Exception:
        return set()


# ─── Scrape Log ───────────────────────────────────────────────────────────────
def log_scrape_run(
    module: str,
    platform: str,
    query: str,
    results_count: int,
    status: str,
    error_msg: str = "",
    duration_sec: int = 0,
):
    """Catat setiap run scraping ke sheet 'Scrape Log'."""
    try:
        row = [
            now_wita(),
            module,
            platform,
            query,
            str(results_count),
            status,
            error_msg,
            str(duration_sec),
        ]
        append_rows_to_sheet("Scrape Log", [row])
    except Exception as e:
        logger = get_logger("scrape-log")
        logger.warning(f"Gagal menulis Scrape Log: {e}")
