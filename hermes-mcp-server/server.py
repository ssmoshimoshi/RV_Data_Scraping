"""
Hermes MCP Server — Module A: Infrastructure & MCP
====================================================
Menghubungkan agen AI ke Google Sheets pipeline intelijen bisnis PT Estetika Ruang Visual.

Mendukung 2 mode koneksi:
  1. Google Apps Script Webhook (Instant, tanpa GCP Console service-account.json)
  2. Google Sheets API v4 (Service Account JSON)

Tools yang diekspos:
  - create_sheet       : Membuat worksheet baru di spreadsheet
  - read_sheet         : Membaca data baris dari worksheet
  - append_row         : Menambahkan 1 baris baru ke sheet
  - append_rows        : Menambahkan sekumpulan baris ke sheet
  - clear_sheet_data   : Mengosongkan data sheet (menjaga header)
  - get_pipeline_summary: Menampilkan ringkasan jumlah lead & status di setiap sheet
"""

import csv
import io
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

# ─── Load Environment Variables ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
# Load hermes-mcp-server/.env first, then root .env as fallback
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(BASE_DIR / "credentials" / "service-account.json"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1mDx0aQcz95iPN6KwdmRgb2RE2xVNIhAgiuoq96k6dAU").strip()
SPREADSHEET_URL = os.getenv("SPREADSHEET_URL", f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit").strip()
WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─── Logging Setup (Only to stderr & file to prevent corrupting stdio MCP) ────
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "hermes_mcp.log"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
log = logging.getLogger("hermes-mcp")

# ─── Service Account Helpers (Optional Fallback) ──────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _get_service_account_path() -> Optional[Path]:
    p = Path(SERVICE_ACCOUNT_FILE)
    if not p.is_absolute():
        p = BASE_DIR / p
    return p if p.exists() else None

def _get_sheets_service():
    sa_path = _get_service_account_path()
    if not sa_path:
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        credentials = service_account.Credentials.from_service_account_file(
            str(sa_path), scopes=SCOPES
        )
        return build("sheets", "v4", credentials=credentials)
    except Exception as e:
        log.warning(f"Gagal inisialisasi Service Account Google Sheets: {e}")
        return None

# ─── Webhook Helpers ──────────────────────────────────────────────────────────
def _send_webhook_request(payload: dict) -> dict:
    if not WEBHOOK_URL:
        raise ValueError("GOOGLE_SHEET_WEBHOOK_URL belum diset di file .env")
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode("utf-8")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"status": "ok", "raw": content}

def _fetch_sheet_csv(sheet_name: str, range_notation: str = "") -> list[list[str]]:
    encoded_sheet = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
    if range_notation:
        url += f"&range={urllib.parse.quote(range_notation)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        content = resp.read().decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        return [row for row in reader if any(cell.strip() for cell in row)]

# ─── Initialize MCP Server ────────────────────────────────────────────────────
mcp = MCPServer("hermes-gsheets")

@mcp.tool()
def get_pipeline_summary() -> str:
    """Mendapatkan ringkasan status lembar data Ruang Visual (Radar Prospek, Matriks Kompetitor, Market Signals)."""
    tabs = ["Radar Prospek", "Matriks Kompetitor", "Market Signals"]
    summary = []
    summary.append(f"**Google Sheets Status**: [Buka Spreadsheet]({SPREADSHEET_URL})")
    summary.append(f"Spreadsheet ID: `{SPREADSHEET_ID}`")
    summary.append(f"Koneksi: {'Webhook Google Apps Script' if WEBHOOK_URL else 'GCP Service Account'}")
    summary.append("\n**Data Lembar Kerja:**")
    
    for tab in tabs:
        try:
            rows = _fetch_sheet_csv(tab)
            count = max(0, len(rows) - 1)
            summary.append(f"- **{tab}**: {count} baris data tercatat")
        except Exception as e:
            summary.append(f"- **{tab}**: Error membaca data ({str(e)})")
            
    return "\n".join(summary)

@mcp.tool()
def create_sheet(sheet_title: str) -> str:
    """Membuat worksheet (tab) baru di dalam Google Spreadsheet Ruang Visual."""
    log.info(f"create_sheet dipanggil: {sheet_title}")
    service = _get_sheets_service()
    if service:
        body = {"requests": [{"addSheet": {"properties": {"title": sheet_title}}}]}
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body=body
        ).execute()
        sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
        return f"Sheet '{sheet_title}' berhasil dibuat via API (sheetId: {sheet_id})."
    
    if WEBHOOK_URL:
        # Webhook otomatis membuat tab jika belum ada saat diberi action append
        res = _send_webhook_request({"sheet_name": sheet_title, "action": "append", "rows": []})
        return f"Sheet '{sheet_title}' dipastikan aktif via Webhook (status: {res.get('status', 'ok')})."
    
    raise ValueError("Tidak ada koneksi aktif (Service Account JSON maupun GOOGLE_SHEET_WEBHOOK_URL tidak ditemukan).")

@mcp.tool()
def read_sheet(sheet_name: str, range_notation: str = "") -> str:
    """Membaca baris data dari sebuah worksheet (misal 'Radar Prospek' atau 'Matriks Kompetitor')."""
    log.info(f"read_sheet dipanggil: {sheet_name} (range: {range_notation})")
    service = _get_sheets_service()
    if service:
        range_str = f"{sheet_name}!{range_notation}" if range_notation else sheet_name
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=range_str)
            .execute()
        )
        rows = result.get("values", [])
    else:
        rows = _fetch_sheet_csv(sheet_name, range_notation)
        
    if not rows:
        return f"Sheet '{sheet_name}' kosong atau belum ada data."
    
    formatted = json.dumps(rows, ensure_ascii=False, indent=2)
    return f"Data dari '{sheet_name}' ({len(rows)} baris):\n```json\n{formatted}\n```"

@mcp.tool()
def append_row(sheet_name: str, row_values: List[str]) -> str:
    """Menambahkan satu baris baru ke dalam worksheet di Google Sheets."""
    return append_rows(sheet_name=sheet_name, rows=[row_values])

@mcp.tool()
def append_rows(sheet_name: str, rows: List[List[str]]) -> str:
    """Menambahkan beberapa baris baru sekaligus ke dalam worksheet (otomatis deduplikasi di server)."""
    log.info(f"append_rows dipanggil: sheet='{sheet_name}', {len(rows)} baris")
    if not rows:
        return "Tidak ada baris yang dikirim."
        
    if WEBHOOK_URL:
        res = _send_webhook_request({
            "sheet_name": sheet_name,
            "action": "append",
            "rows": rows
        })
        return f"Berhasil mengirim {len(rows)} baris ke sheet '{sheet_name}' via Webhook (Response: {res.get('status', 'ok')})."
        
    service = _get_sheets_service()
    if service:
        body = {"values": rows}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range=sheet_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        updated = result.get("updates", {}).get("updatedRows", len(rows))
        return f"Berhasil menambahkan {updated} baris ke '{sheet_name}' via Google Sheets API."
        
    raise ValueError("Tidak dapat menulis: GOOGLE_SHEET_WEBHOOK_URL atau Service Account JSON belum dikonfigurasi.")

@mcp.tool()
def clear_sheet_data(sheet_name: str) -> str:
    """Mengosongkan isi data pada worksheet tertentu dengan tetap mempertahankan baris header pertama."""
    log.info(f"clear_sheet_data dipanggil: {sheet_name}")
    if WEBHOOK_URL:
        res = _send_webhook_request({
            "sheet_name": sheet_name,
            "action": "clear_data",
            "rows": []
        })
        return f"Data sheet '{sheet_name}' berhasil dikosongkan (header tetap aman)."
        
    service = _get_sheets_service()
    if service:
        range_str = f"{sheet_name}!A2:Z10000"
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=range_str
        ).execute()
        return f"Data di '{sheet_name}' baris 2 ke bawah berhasil dikosongkan."
        
    raise ValueError("Tidak ada koneksi aktif untuk mengosongkan sheet.")

# ─── Entry Point ──────────────────────────────────────────────────────────────
def main():
    log.info("Memulai Hermes MCP Server (transport: stdio)...")
    log.info(f"Spreadsheet ID: {SPREADSHEET_ID}")
    log.info(f"Webhook Active: {bool(WEBHOOK_URL)}")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
