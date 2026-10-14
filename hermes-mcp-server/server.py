"""
Hermes MCP Server — Module A: Infrastructure & MCP
====================================================
Menghubungkan agen Hermes ke Google Sheets via Model Context Protocol (stdio).

Tools yang diekspos:
  - create_sheet   : Membuat worksheet baru di spreadsheet
  - read_sheet     : Membaca semua baris dari sebuah sheet
  - append_row     : Menambahkan baris baru ke sheet
  - update_cell    : Memperbarui nilai satu sel spesifik
"""

import os
import json
import logging
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from googleapiclient.discovery import build
from google.oauth2 import service_account

# ─── Load Environment Variables ───────────────────────────────────────────────
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service-account.json")
SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID", "")
LOG_LEVEL            = os.getenv("LOG_LEVEL", "INFO")

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/hermes_mcp.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("hermes-mcp")

# ─── Google Sheets Client ─────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    """Membuat dan mengembalikan Google Sheets API service menggunakan Service Account."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"Service Account file tidak ditemukan: '{SERVICE_ACCOUNT_FILE}'. "
            "Letakkan file JSON GCP di folder credentials/ dan update .env Anda."
        )
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=credentials)


# ─── MCP Server Instance ──────────────────────────────────────────────────────
app = Server("hermes-gsheets-server")


# ─── Tool Definitions ─────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """Mendaftarkan semua tools yang tersedia ke MCP host (Hermes/Antigravity IDE)."""
    return [
        types.Tool(
            name="create_sheet",
            description=(
                "Membuat worksheet (tab) baru di dalam Google Spreadsheet yang sudah dikonfigurasi. "
                "Gunakan ini untuk menginisialisasi 'Radar Prospek' atau 'Matriks Kompetitor'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sheet_title": {
                        "type": "string",
                        "description": "Nama tab/worksheet baru yang akan dibuat.",
                    }
                },
                "required": ["sheet_title"],
            },
        ),
        types.Tool(
            name="read_sheet",
            description=(
                "Membaca semua baris dari sebuah worksheet. "
                "Mengembalikan data dalam format list of lists."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Nama tab worksheet yang ingin dibaca.",
                    },
                    "range_notation": {
                        "type": "string",
                        "description": "Rentang sel opsional, contoh: 'A1:F100'. Default: seluruh sheet.",
                        "default": "",
                    },
                },
                "required": ["sheet_name"],
            },
        ),
        types.Tool(
            name="append_row",
            description=(
                "Menambahkan satu baris baru di akhir data pada sebuah worksheet. "
                "Gunakan ini untuk memasukkan data lead baru atau entri kompetitor."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Nama tab worksheet tujuan.",
                    },
                    "row_values": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List nilai untuk setiap kolom dalam satu baris.",
                    },
                },
                "required": ["sheet_name", "row_values"],
            },
        ),
        types.Tool(
            name="update_cell",
            description=(
                "Memperbarui nilai satu sel spesifik menggunakan notasi A1. "
                "Gunakan ini untuk mengubah Skor Prospek atau Status Akuisisi pada baris tertentu."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Nama tab worksheet.",
                    },
                    "cell_notation": {
                        "type": "string",
                        "description": "Notasi sel A1, contoh: 'F3' atau 'C10'.",
                    },
                    "value": {
                        "type": "string",
                        "description": "Nilai baru yang akan ditulis ke sel tersebut.",
                    },
                },
                "required": ["sheet_name", "cell_notation", "value"],
            },
        ),
    ]


# ─── Tool Handlers ────────────────────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Router utama: meneruskan panggilan tool ke handler yang sesuai."""
    log.info(f"Tool dipanggil: '{name}' | Args: {json.dumps(arguments, ensure_ascii=False)}")
    try:
        if name == "create_sheet":
            return await _create_sheet(arguments)
        elif name == "read_sheet":
            return await _read_sheet(arguments)
        elif name == "append_row":
            return await _append_row(arguments)
        elif name == "update_cell":
            return await _update_cell(arguments)
        else:
            raise ValueError(f"Tool tidak dikenal: '{name}'")
    except Exception as e:
        log.error(f"Error saat menjalankan tool '{name}': {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"ERROR: {str(e)}")]


async def _create_sheet(args: dict) -> list[types.TextContent]:
    """Membuat worksheet baru di spreadsheet."""
    title = args["sheet_title"]
    service = get_sheets_service()
    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    response = service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body=body
    ).execute()
    sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
    msg = f"Sheet '{title}' berhasil dibuat (sheetId: {sheet_id})."
    log.info(msg)
    return [types.TextContent(type="text", text=msg)]


async def _read_sheet(args: dict) -> list[types.TextContent]:
    """Membaca data dari worksheet."""
    sheet_name = args["sheet_name"]
    range_notation = args.get("range_notation", "")
    range_str = f"{sheet_name}!{range_notation}" if range_notation else sheet_name
    service = get_sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=range_str)
        .execute()
    )
    rows = result.get("values", [])
    if not rows:
        return [types.TextContent(type="text", text=f"Sheet '{sheet_name}' kosong atau tidak ada data.")]
    formatted = json.dumps(rows, ensure_ascii=False, indent=2)
    msg = f"Data dari '{sheet_name}' ({len(rows)} baris):\n```json\n{formatted}\n```"
    log.info(f"Berhasil membaca {len(rows)} baris dari '{sheet_name}'.")
    return [types.TextContent(type="text", text=msg)]


async def _append_row(args: dict) -> list[types.TextContent]:
    """Menambahkan satu baris baru ke worksheet."""
    sheet_name = args["sheet_name"]
    row_values  = args["row_values"]
    service = get_sheets_service()
    body = {"values": [row_values]}
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
    updates = result.get("updates", {})
    msg = f"Baris berhasil ditambahkan ke '{sheet_name}'. Baris diperbarui: {updates.get('updatedRows', 1)}."
    log.info(msg)
    return [types.TextContent(type="text", text=msg)]


async def _update_cell(args: dict) -> list[types.TextContent]:
    """Memperbarui satu sel spesifik."""
    sheet_name    = args["sheet_name"]
    cell_notation = args["cell_notation"]
    value         = args["value"]
    range_str = f"{sheet_name}!{cell_notation}"
    service = get_sheets_service()
    body = {"values": [[value]]}
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_str,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()
    msg = f"Sel '{range_str}' berhasil diperbarui dengan nilai: '{value}'."
    log.info(msg)
    return [types.TextContent(type="text", text=msg)]


# ─── Entrypoint ───────────────────────────────────────────────────────────────

async def main():
    log.info("Hermes MCP Server dimulai (transport: stdio)...")
    if not SPREADSHEET_ID:
        log.warning("SPREADSHEET_ID belum diset di file .env!")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
