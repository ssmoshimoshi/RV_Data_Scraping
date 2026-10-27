import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from scrapers.dashboard_server import enrich_lead_card
from scrapers.sample_leads import SAMPLE_LEADS

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "hermes-mcp-server" / ".env")

WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()

CATEGORY_DISPLAY_NAMES = {
    "fnb_beverage": "F&B / Kedai Kopi & Minuman",
    "fnb_restaurant": "F&B / Roastery & Resto",
    "fashion": "Fashion / Modern Boutique",
    "healthcare": "Klinik Estetika & Gigi",
    "corporate": "Notaris & Legal Office",
    "chain_fnb": "F&B / Retail Chain",
}

RADAR_PROSPEK_HEADERS = [
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
    "Tanggal",
]


def format_lead_for_radar_prospek(lead_card: Dict[str, Any]) -> List[str]:
    enriched = enrich_lead_card(lead_card)
    cat_raw = enriched.get("category", "Umum")
    cat_label = CATEGORY_DISPLAY_NAMES.get(cat_raw, cat_raw.replace("_", " ").title())
    
    score = enriched.get("lead_score", 0)
    tier = enriched.get("priority_tier", "Tier B")
    wa_num = enriched.get("whatsapp_number", "-")
    wa_link = enriched.get("wa_link") or (f"https://wa.me/{wa_num}" if wa_num and wa_num != "-" else "-")
    
    products = enriched.get("recommended_products") or []
    products_str = ", ".join(products[:4]) if products else "-"
    
    reason = enriched.get("reason_summary") or enriched.get("value_proposition") or "-"
    address = enriched.get("address_full") or "-"
    rating_val = enriched.get("rating", 0)
    rev_count = enriched.get("reviews_count", 0)
    rating_str = f"{rating_val} ({rev_count} ulasan)" if rating_val else "-"
    
    website = enriched.get("external_website_url") or "-"
    lat = enriched.get("latitude")
    lng = enriched.get("longitude")
    maps_link = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else "-"
    date_str = datetime.now().strftime("%Y-%m-%d")

    return [
        enriched.get("business_name", "Tanpa Nama"),
        cat_label,
        enriched.get("platform", "Google Maps").replace("_", " ").title(),
        str(score),
        f"{tier} (Skor {score})",
        wa_num,
        wa_link,
        products_str,
        reason,
        address,
        rating_str,
        website,
        maps_link,
        date_str,
    ]


def send_webhook_payload(payload: Dict[str, Any], webhook_url: Optional[str] = None) -> Dict[str, Any]:
    url = WEBHOOK_URL if webhook_url is None else webhook_url
    if not url:
        raise ValueError("GOOGLE_SHEET_WEBHOOK_URL belum dikonfigurasi pada file .env")
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode("utf-8")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"status": "ok", "raw": content}


def sync_leads_to_hermes(
    leads: Optional[List[Dict[str, Any]]] = None,
    sheet_name: str = "Radar Prospek",
    clear_first: bool = False,
    dry_run: bool = False,
    webhook_url: Optional[str] = None,
) -> Dict[str, Any]:
    target_leads = leads if leads is not None else SAMPLE_LEADS
    rows = [format_lead_for_radar_prospek(l) for l in target_leads]

    if dry_run:
        return {
            "status": "dry_run",
            "sheet_name": sheet_name,
            "clear_first": clear_first,
            "rows_count": len(rows),
            "sample_rows": rows[:2],
        }

    url = webhook_url or WEBHOOK_URL
    if not url:
        return {
            "status": "error",
            "message": "GOOGLE_SHEET_WEBHOOK_URL tidak ditemukan. Mode pengiriman dilewati.",
            "rows_count": len(rows),
        }

    if clear_first:
        send_webhook_payload({"sheet_name": sheet_name, "action": "clear_data", "rows": []}, webhook_url=url)

    resp = send_webhook_payload({"sheet_name": sheet_name, "action": "append", "rows": rows}, webhook_url=url)
    return {
        "status": "success",
        "sheet_name": sheet_name,
        "rows_count": len(rows),
        "webhook_response": resp,
    }


def main():
    parser = argparse.ArgumentParser(description="Sinkronisasi prospek lokal ke Google Sheets Hermes")
    parser.add_argument("--dry-run", action="store_true", help="Uji tanpa menulis ke Google Sheets")
    parser.add_argument("--clear-first", action="store_true", help="Kosongkan data lama di sheet sebelum mengunggah")
    parser.add_argument("--limit", type=int, default=0, help="Batasi jumlah baris yang disinkronkan")
    args = parser.parse_args()

    leads = SAMPLE_LEADS[:args.limit] if args.limit > 0 else SAMPLE_LEADS
    print(f"Memulai sinkronisasi ke Google Sheets Hermes (Total prospek: {len(leads)})...")
    
    result = sync_leads_to_hermes(
        leads=leads,
        clear_first=args.clear_first,
        dry_run=args.dry_run,
    )
    
    print(f"Status: {result.get('status')}")
    print(f"Jumlah baris: {result.get('rows_count')}")
    if args.dry_run:
        print("Sampel baris pertama:")
        print(json.dumps(result.get("sample_rows", [])[0], indent=2))
    else:
        print(f"Hasil respons webhook: {result.get('webhook_response')}")


if __name__ == "__main__":
    main()
