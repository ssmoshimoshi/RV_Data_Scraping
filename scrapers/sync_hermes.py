import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import csv
import io
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from scrapers.dashboard_server import enrich_lead_card
from scrapers.sample_leads import SAMPLE_LEADS
from scrapers.normalizer import normalize_whatsapp
from scrapers.db_sqlite import DB_PATH, init_db, upsert_lead

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "hermes-mcp-server" / ".env")

DEFAULT_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwHCyHBZ1qEl8Mz4Fv9ClVtUIu6vDRuSvRZxFe8YmdYRRPgkoEdFTOSGC7nX9ymgvw/exec"
WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip() or DEFAULT_WEBHOOK_URL
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1mDx0aQcz95iPN6KwdmRgb2RE2xVNIhAgiuoq96k6dAU").strip()

CATEGORY_DISPLAY_NAMES = {
    "fnb_beverage": "F&B / Kedai Kopi & Minuman",
    "fnb_restaurant": "F&B / Roastery & Resto",
    "fashion": "Fashion / Modern Boutique",
    "healthcare": "Klinik Estetika & Gigi",
    "corporate": "Notaris & Legal Office",
    "chain_fnb": "F&B / Retail Chain",
}

INV_CATEGORY_DISPLAY_NAMES = {
    "f&b / kedai kopi & minuman": "fnb_beverage",
    "f&b / roastery & resto": "fnb_restaurant",
    "fnb food resto": "fnb_restaurant",
    "fnb hospitality": "fnb_hospitality",
    "fashion / modern boutique": "fashion",
    "fashion retail": "fashion",
    "klinik estetika & gigi": "healthcare",
    "beauty skincare": "healthcare",
    "notaris & legal office": "corporate",
    "corporate legal": "corporate",
    "f&b / retail chain": "chain_fnb",
    "new store opening": "new_store_opening",
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
    if leads is not None:
        target_leads = leads
    else:
        from scrapers.dashboard_server import get_all_leads
        target_leads = get_all_leads()
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


def fetch_sheet_rows(sheet_name: str = "Radar Prospek", spreadsheet_id: Optional[str] = None) -> List[List[str]]:
    sid = spreadsheet_id or SPREADSHEET_ID
    encoded_sheet = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        content = resp.read().decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        return [row for row in reader if any(cell.strip() for cell in row)]


def pull_leads_from_hermes(
    sheet_name: str = "Radar Prospek",
    db_path: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    target_db = Path(db_path) if db_path else DB_PATH
    init_db(target_db)

    rows = fetch_sheet_rows(sheet_name=sheet_name)
    if not rows or len(rows) <= 1:
        return {
            "status": "empty",
            "sheet_name": sheet_name,
            "total_rows": 0,
            "imported_count": 0,
            "updated_count": 0
        }

    conn = sqlite3.connect(str(target_db))
    cursor = conn.cursor()
    cursor.execute("SELECT entity_id, business_name, whatsapp_number FROM entities")
    existing_rows = cursor.fetchall()
    conn.close()

    wa_to_id = {r[2]: r[0] for r in existing_rows if r[2]}
    name_to_id = {r[1].lower().strip(): r[0] for r in existing_rows if r[1]}

    num_ids = []
    for r in existing_rows:
        eid = r[0]
        if eid.startswith("ent_"):
            suffix = eid[4:]
            if suffix.isdigit():
                num_ids.append(int(suffix))
    next_num = (max(num_ids) + 1) if num_ids else 1

    imported_count = 0
    updated_count = 0
    processed_entities = []

    DUMMY_NAMES = {
        'kopi titik temu makassar',
        'dapur bunda roastery & resto',
        'ayu hijab & modern boutique',
        'aesthetic glow dental clinic',
        'grand opening kopi kenangan pettarani',
        'kantor notaris & ppat ahmad fauzi sh mkn'
    }

    for r in rows[1:]:
        name = r[0].strip() if len(r) > 0 else ""
        if not name or name.lower() == "nama bisnis" or name.lower().strip() in DUMMY_NAMES:
            continue

        cat_str = r[1].strip() if len(r) > 1 else ""
        platform_str = r[2].strip() if len(r) > 2 else "Google Maps"
        score_str = r[3].strip() if len(r) > 3 else "50"
        status_str = r[4].strip() if len(r) > 4 else "Tier D"
        wa_raw = r[5].strip() if len(r) > 5 else ""
        recs_str = r[7].strip() if len(r) > 7 else ""
        pitch_str = r[8].strip() if len(r) > 8 else ""
        addr_str = r[9].strip() if len(r) > 9 else ""
        rating_str = r[10].strip() if len(r) > 10 else ""
        web_str = r[11].strip() if len(r) > 11 else ""
        maps_str = r[12].strip() if len(r) > 12 else ""

        wa = normalize_whatsapp(wa_raw) if wa_raw else None
        cat_key = INV_CATEGORY_DISPLAY_NAMES.get(cat_str.lower().strip())
        if not cat_key:
            cat_key = re.sub(r'[^a-z0-9]+', '_', cat_str.lower()).strip('_') or "general_commercial"

        entity_id = None
        if wa and wa in wa_to_id:
            entity_id = wa_to_id[wa]
        elif name.lower().strip() in name_to_id:
            entity_id = name_to_id[name.lower().strip()]

        is_new = False
        if not entity_id:
            is_new = True
            entity_id = f"ent_{next_num:04d}"
            next_num += 1
            name_to_id[name.lower().strip()] = entity_id
            if wa:
                wa_to_id[wa] = entity_id

        rating_val = 4.5
        revs_count = 0
        if rating_str and rating_str != "-":
            m_r = re.search(r'(\d+(?:\.\d+)?)', rating_str)
            if m_r:
                try:
                    rating_val = float(m_r.group(1))
                except ValueError:
                    pass
            m_c = re.search(r'\((\d+)\s*ulasan\)', rating_str)
            if m_c:
                try:
                    revs_count = int(m_c.group(1))
                except ValueError:
                    pass

        score_val = 50
        if score_str and score_str.strip().isdigit():
            score_val = int(score_str.strip())

        tier_val = "Tier D"
        for t in ["Tier A", "Tier B", "Tier C", "Tier D"]:
            if t in status_str:
                tier_val = t
                break

        clean_addr = addr_str if addr_str and not addr_str.startswith("[object") and addr_str != "-" else ""
        clean_web = web_str if web_str and web_str != "-" else ""
        if not clean_web and maps_str and maps_str.startswith("http"):
            clean_web = maps_str

        payload = {
            "entity_id": entity_id,
            "business_name": name,
            "target_sector": cat_key,
            "primary_service_pillar": "packaging_box",
            "category_raw": cat_str,
            "whatsapp_number": wa,
            "phone_raw": wa_raw or None,
            "is_wa_valid": 1 if wa else 0,
            "is_commercial": 1,
            "locations": {
                "address_full": clean_addr,
                "city": "Makassar",
            },
            "digital_footprints": {
                "website_url": clean_web,
                "gmaps_rating": rating_val,
                "gmaps_reviews_count": revs_count,
            },
            "commercial_intelligence": {
                "lead_score": score_val,
                "priority_tier": tier_val,
                "recommended_products": recs_str,
            },
            "outreach_logs": {
                "outreach_status": "Belum Dihubungi",
                "whatsapp_pitch": pitch_str,
            }
        }

        if not dry_run:
            upsert_lead(payload, db_path=str(target_db))

        if is_new:
            imported_count += 1
        else:
            updated_count += 1
        processed_entities.append(entity_id)

    return {
        "status": "success",
        "sheet_name": sheet_name,
        "total_rows": len(rows) - 1,
        "imported_count": imported_count,
        "updated_count": updated_count,
        "entities_count": len(processed_entities)
    }


def main():
    parser = argparse.ArgumentParser(description="Sinkronisasi prospek lokal ke Google Sheets Hermes")
    parser.add_argument("--direction", choices=["push", "pull"], default="push", help="Arah sinkronisasi: push (unggah ke Sheets) atau pull (tarik dari Sheets)")
    parser.add_argument("--sheet", type=str, default="Radar Prospek", help="Nama tab sheet target")
    parser.add_argument("--dry-run", action="store_true", help="Uji tanpa menulis ke database/Sheets")
    parser.add_argument("--clear-first", action="store_true", help="Kosongkan data lama di sheet sebelum mengunggah (khusus push)")
    parser.add_argument("--limit", type=int, default=0, help="Batasi jumlah baris yang disinkronkan")
    args = parser.parse_args()

    if args.direction == "pull":
        print(f"Menjalankan penarikan data dari Google Sheets '{args.sheet}' (Dry-run: {args.dry_run})...")
        res = pull_leads_from_hermes(sheet_name=args.sheet, dry_run=args.dry_run)
        print(f"Status: {res.get('status')}")
        print(f"Total baris sheet: {res.get('total_rows')}")
        print(f"Baris baru diimpor: {res.get('imported_count')}")
        print(f"Baris diperbarui: {res.get('updated_count')}")
        return

    from scrapers.dashboard_server import get_all_leads
    all_leads = get_all_leads()
    leads = all_leads[:args.limit] if args.limit > 0 else all_leads
    print(f"Memulai sinkronisasi ke Google Sheets Hermes (Total prospek: {len(leads)})...")
    
    result = sync_leads_to_hermes(
        leads=leads,
        sheet_name=args.sheet,
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
