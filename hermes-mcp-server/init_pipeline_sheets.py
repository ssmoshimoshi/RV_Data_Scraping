"""
Hermes Pipeline — Inisialisasi Google Sheets Otomatis
=====================================================
Memverifikasi koneksi Google Sheets (Webhook atau Service Account)
dan memastikan tab utama sesuai spesifikasi PRD Ruang Visual aktif:
  1. Radar Prospek
  2. Matriks Kompetitor
  3. Market Signals
"""

import json
import os
import sys
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(BASE_DIR / "credentials" / "service-account.json"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "").strip()
WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()

TARGET_SHEETS = {
    "Radar Prospek": [
        "Nama Bisnis", "Kategori", "Skor", "Status", "No. WhatsApp",
        "Link WA", "Proyeksi Kebutuhan Cetak", "Alamat", "Rating & Ulasan",
        "Website", "Peta Lokasi", "Tanggal"
    ],
    "Matriks Kompetitor": [
        "Nama Percetakan", "Fokus Layanan Utama", "Kapasitas / Skala",
        "Rating & Ulasan", "No. WhatsApp", "Link WA", "Celah Kualitas",
        "Celah Pelayanan & SOP", "Selling Point RUANG VISUAL", "Website / Maps", "Tanggal Update"
    ],
    "Market Signals": [
        "Sinyal / Tren Produk", "Platform", "Tingkat Demand",
        "Peluang untuk RUANG VISUAL", "Link Referensi", "Tanggal"
    ]
}

def initialize_via_webhook():
    print(f"Menginisialisasi tab Google Sheets via Webhook Apps Script...")
    for sheet_name, headers in TARGET_SHEETS.items():
        payload = {
            "sheet_name": sheet_name,
            "action": "append",
            "rows": []
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(WEBHOOK_URL, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"   [OK] Tab '{sheet_name}' aktif dan terverifikasi.")
        except Exception as e:
            print(f"   [WARN] Gagal verifikasi tab '{sheet_name}': {e}")
    print("\nInisialisasi via Webhook SELESAI.")

def initialize_via_service_account():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    print("Menghubungkan ke Google Sheets API via Service Account...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=scopes
    )
    service = build("sheets", "v4", credentials=credentials)

    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = [s["properties"]["title"] for s in sheet_metadata.get("sheets", [])]
    print(f"Spreadsheet terdeteksi: '{sheet_metadata.get('properties', {}).get('title', '')}'")
    print(f"Tab yang sudah ada: {existing_sheets}")

    requests = []
    for title in TARGET_SHEETS.keys():
        if title not in existing_sheets:
            print(f"Menyiapkan tab baru: '{title}'...")
            requests.append({"addSheet": {"properties": {"title": title}}})

    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests}
        ).execute()
        print("Tab berhasil dibuat.")

    for title, headers in TARGET_SHEETS.items():
        range_name = f"{title}!A1:Z1"
        current_data = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=range_name
        ).execute().get("values", [])

        if not current_data:
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{title}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [headers]}
            ).execute()
            print(f"   Header berhasil ditulis di '{title}'.")
        else:
            print(f"   Header di '{title}' sudah ada, tidak ditimpa.")

    print("\nInisialisasi via Service Account SELESAI.")

def main():
    sa_path = Path(SERVICE_ACCOUNT_FILE)
    if not sa_path.is_absolute():
        sa_path = BASE_DIR / sa_path

    if sa_path.exists() and SPREADSHEET_ID:
        initialize_via_service_account()
    elif WEBHOOK_URL:
        initialize_via_webhook()
    else:
        print("[ERROR] Tidak ada kredensial valid (GOOGLE_SHEET_WEBHOOK_URL atau Service Account JSON belum diset).")
        sys.exit(1)

if __name__ == "__main__":
    main()
