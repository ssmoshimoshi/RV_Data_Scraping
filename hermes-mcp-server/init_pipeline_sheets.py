"""
Hermes Pipeline — Inisialisasi Google Sheets Otomatis
=====================================================
Memverifikasi kredensial Service Account dan membuat 2 sheet utama
sesuai spesifikasi PRD Section 4:
  1. Radar Prospek
  2. Matriks Kompetitor
"""

import os
import sys
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service-account.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "").strip()

def check_environment():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ File kredensial tidak ditemukan: {SERVICE_ACCOUNT_FILE}")
        print("   Pastikan file JSON Service Account sudah diletakkan di folder credentials/")
        return False

    if not SPREADSHEET_ID or SPREADSHEET_ID == "your-spreadsheet-id-here":
        print("❌ SPREADSHEET_ID belum diisi di file .env!")
        return False

    return True

def initialize_sheets():
    if not check_environment():
        sys.exit(1)

    print(f"🔍 Menghubungkan ke Google Sheets API...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=scopes
    )
    service = build("sheets", "v4", credentials=credentials)

    # 1. Dapatkan info spreadsheet yang ada
    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = [s["properties"]["title"] for s in sheet_metadata.get("sheets", [])]
    print(f"📄 Spreadsheet terdeteksi: '{sheet_metadata.get('properties', {}).get('title', '')}'")
    print(f"   Tab yang sudah ada: {existing_sheets}")

    # Struktur kolom sesuai PRD
    target_sheets = {
        "Radar Prospek": [
            "Entitas Bisnis",
            "Kategori Segmen",
            "Trigger Event",
            "Proyeksi Kebutuhan",
            "Skor Prospek",
            "Status Akuisisi"
        ],
        "Matriks Kompetitor": [
            "Nama Kompetitor",
            "Fokus Layanan Utama",
            "Celah Kualitas",
            "Celah SOP/Admin",
            "Estimasi Kapasitas",
            "Estetika Visual"
        ]
    }

    # 2. Buat tab jika belum ada
    requests = []
    for title in target_sheets.keys():
        if title not in existing_sheets:
            print(f"➕ Menyiapkan tab baru: '{title}'...")
            requests.append({"addSheet": {"properties": {"title": title}}})

    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests}
        ).execute()
        print("✅ Tab berhasil dibuat!")

    # 3. Tulis Header Kolom
    for title, headers in target_sheets.items():
        print(f"📝 Memeriksa header untuk '{title}'...")
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
            print(f"   ✅ Header berhasil ditulis di '{title}': {headers}")
        else:
            print(f"   ℹ️ Header di '{title}' sudah ada, tidak ditimpa.")

    print("\n🎉 INISIALISASI SELESAI! Google Sheets siap digunakan oleh Hermes.")

if __name__ == "__main__":
    initialize_sheets()
