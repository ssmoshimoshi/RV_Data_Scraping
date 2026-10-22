# Hermes MCP Server
> **Module A — Infrastructure & MCP** | PT Estetika Ruang Visual

Server MCP lokal (stdio) yang menghubungkan agen Hermes ke Google Sheets sebagai database utama pipeline intelijen bisnis.

---

## Struktur Direktori

```
hermes-mcp-server/
├── server.py               # Entry point — MCP server utama
├── requirements.txt        # Python dependencies
├── .env.example            # Template environment variables
├── .env                    # (Buat sendiri, jangan di-commit!)
├── .gitignore
├── credentials/
│   └── service-account.json  # (Buat sendiri dari GCP, jangan di-commit!)
├── tools/                  # (Untuk modul lanjutan: scraper, dll.)
└── logs/
    └── hermes_mcp.log      # Log runtime (auto-generated)
```

---

## Setup (Langkah demi Langkah)

### 1. Buat Virtual Environment
```bash
cd hermes-mcp-server
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Siapkan GCP Service Account
1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru (atau gunakan yang ada)
3. Aktifkan **Google Sheets API**
4. Buat **Service Account** → Download kunci JSON
5. Letakkan file JSON di: `credentials/service-account.json`
6. Di Google Spreadsheet Anda, **share** spreadsheet ke email service account (dengan akses Editor)

### 4. Konfigurasi Environment
```bash
cp .env.example .env
```
Edit `.env`:
```
GOOGLE_SERVICE_ACCOUNT_FILE=credentials/service-account.json
SPREADSHEET_ID=<ID dari URL spreadsheet Anda>
LOG_LEVEL=INFO
```

### 5. Daftarkan ke Antigravity IDE
Tambahkan konfigurasi berikut ke MCP config Antigravity IDE:
```json
{
  "mcpServers": {
    "hermes-gsheets": {
      "command": "/path/to/hermes-mcp-server/.venv/bin/python",
      "args": ["/path/to/hermes-mcp-server/server.py"],
      "env": {}
    }
  }
}
```

---

## Tools yang Tersedia

| Tool | Deskripsi | Parameter Wajib |
|------|-----------|-----------------|
| `create_sheet` | Membuat tab worksheet baru | `sheet_title` |
| `read_sheet` | Membaca semua baris dari sheet | `sheet_name` |
| `append_row` | Menambahkan baris baru | `sheet_name`, `row_values` |
| `update_cell` | Memperbarui satu sel (notasi A1) | `sheet_name`, `cell_notation`, `value` |

---

## Inisialisasi Sheet (Sesuai PRD)

Setelah server aktif, minta Hermes menjalankan:
```
create_sheet("Radar Prospek")
create_sheet("Matriks Kompetitor")
```

Kemudian tambahkan header baris pertama via `append_row`.

---

*Bagian dari: Automated Market Intelligence & Lead Generation Pipeline — RUANG VISUAL*
