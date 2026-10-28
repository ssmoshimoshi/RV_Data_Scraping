import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import math
import sqlite3
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from scrapers.gmaps_scraper import search_places
from scrapers.normalizer import normalize_whatsapp, normalize_address
from scrapers.lead_scoring import calculate_4_pillars_score, classify_category
from scrapers.sync_hermes import sync_leads_to_hermes
from scrapers.db_sqlite import init_db as init_normalized_db, upsert_lead as upsert_lead_sqlite
from scrapers.outreach_generator import generate_outreach_pitch, recommended_products

STATE_FILE = PROJECT_ROOT / "data" / "search_state.json"
LEADS_DB = PROJECT_ROOT / "data" / "leads.sqlite"

LAT_ORIGIN = -5.15759432245317
LON_ORIGIN = 119.43530577903459

SECTOR_QUERIES = {
    "fnb_hospitality": ["kafe", "kedai kopi", "roastery", "restoran", "bakery", "toko kue", "katering"],
    "retail_apparel": ["butik pakaian", "hijab store", "distro clothing", "toko baju"],
    "beauty_skincare": ["klinik kecantikan", "klinik estetika", "dokter gigi", "salon", "spa"],
    "corporate_legal": ["notaris ppat", "kantor hukum", "advokat", "konsultan hukum"],
    "event_wedding": ["wedding organizer", "event planner", "dekorasi pesta", "wedding decoration"]
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "center_lat": LAT_ORIGIN,
        "center_lon": LON_ORIGIN,
        "current_radius_km": 1,
        "current_sector_index": 0,
        "completed_sectors_in_radius": [],
        "seen_place_ids": [],
        "last_scraped_at": None
    }


def save_state(state: Dict[str, Any]):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def init_db():
    LEADS_DB.parent.mkdir(parents=True, exist_ok=True)
    init_normalized_db(LEADS_DB)
    conn = sqlite3.connect(LEADS_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            place_id TEXT PRIMARY KEY,
            business_name TEXT,
            category TEXT,
            whatsapp TEXT,
            address TEXT,
            latitude REAL,
            longitude REAL,
            distance_km REAL,
            lead_score REAL,
            found_at TEXT,
            synced_to_sheet INTEGER DEFAULT 0,
            notified_telegram INTEGER DEFAULT 0,
            status TEXT DEFAULT 'verified',
            created_at TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(leads)")
    cols = [c[1] for c in cursor.fetchall()]
    if "status" not in cols:
        cursor.execute("ALTER TABLE leads ADD COLUMN status TEXT DEFAULT 'verified'")
    if "created_at" not in cols:
        cursor.execute("ALTER TABLE leads ADD COLUMN created_at TEXT")
        cursor.execute("UPDATE leads SET created_at = found_at WHERE created_at IS NULL")
    conn.commit()
    conn.close()


def process_place(
    place: Dict[str, Any],
    details: Optional[Dict[str, Any]],
    origin_lat: float,
    origin_lon: float,
    category: str
) -> Optional[Dict[str, Any]]:
    place_id = place.get("place_id") or place.get("google_maps_place_id")
    name = place.get("title") or place.get("name") or "Unknown"

    lat = place.get("latitude")
    lon = place.get("longitude")
    if lat is None or lon is None:
        geom_loc = place.get("geometry", {}).get("location", {})
        lat = geom_loc.get("lat")
        lon = geom_loc.get("lng")

    if lat is None or lon is None:
        lat = origin_lat
        lon = origin_lon

    distance = haversine_distance(origin_lat, origin_lon, lat, lon)

    address = place.get("address") or place.get("vicinity") or ""
    phone = place.get("phone_number") or place.get("whatsapp_number")

    if details:
        address = details.get("formatted_address") or address
        detail_phone = details.get("formatted_phone_number") or details.get("international_phone_number")
        if detail_phone:
            phone = detail_phone

    whatsapp = None
    if phone:
        whatsapp = normalize_whatsapp(phone)
    elif place.get("whatsapp_number"):
        whatsapp = normalize_whatsapp(place.get("whatsapp_number"))

    if address:
        address = normalize_address(address)

    scoring_payload = {
        "place_id": place_id,
        "business_name": name,
        "address_full": address,
        "category": category,
        "gmaps_rating": place.get("rating") or place.get("total_score"),
        "reviews_count": place.get("reviews_count", 0),
        "whatsapp_number": whatsapp,
        "is_wa_valid": 1 if whatsapp else 0
    }
    scoring_result = calculate_4_pillars_score(scoring_payload)
    lead_score = scoring_result.get("score_total", 0)

    pitch = generate_outreach_pitch({
        "business_name": name,
        "category": category,
        "rating": place.get("rating"),
        "city": "Makassar"
    })
    recs = recommended_products({"category": category})

    return {
        "place_id": place_id,
        "business_name": name,
        "category": category,
        "whatsapp": whatsapp,
        "whatsapp_number": whatsapp,
        "address": address,
        "address_full": address,
        "latitude": lat,
        "longitude": lon,
        "distance_km": round(distance, 2),
        "lead_score": lead_score,
        "rating": place.get("rating"),
        "reviews_count": place.get("reviews_count", 0),
        "priority_tier": scoring_result.get("tier", "Tier D"),
        "whatsapp_pitch": pitch,
        "recommended_products": recs,
        "found_at": datetime.utcnow().isoformat()
    }


def save_lead(lead: Dict[str, Any], dry_run: bool = False) -> bool:
    if dry_run:
        print(f"[DRY-RUN] Teridentifikasi: {lead['business_name']} ({lead['category']}) | Jarak: {lead['distance_km']} km")
        return True

    conn = sqlite3.connect(LEADS_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO leads 
            (place_id, business_name, category, whatsapp, address, latitude, longitude, distance_km, lead_score, found_at, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'verified', ?)
        """, (
            lead["place_id"],
            lead["business_name"],
            lead["category"],
            lead.get("whatsapp"),
            lead.get("address"),
            lead.get("latitude"),
            lead.get("longitude"),
            lead.get("distance_km"),
            lead.get("lead_score"),
            lead["found_at"],
            lead["found_at"]
        ))
        conn.commit()
    except Exception as e:
        print(f"Gagal menyimpan ke tabel leads: {e}")
    finally:
        conn.close()

    entity_id = f"ent_{lead['place_id'][-8:]}" if lead.get("place_id") else f"ent_{int(time.time())}"
    entity_payload = {
        "entity_id": entity_id,
        "business_name": lead["business_name"],
        "target_sector": lead["category"],
        "primary_service_pillar": "packaging_box",
        "category_raw": lead["category"],
        "whatsapp_number": lead.get("whatsapp"),
        "phone_raw": lead.get("whatsapp"),
        "is_wa_valid": 1 if lead.get("whatsapp") else 0,
        "is_commercial": 1,
        "locations": {
            "place_id": lead["place_id"],
            "address_full": lead.get("address", ""),
            "city": "Makassar",
            "latitude": lead.get("latitude"),
            "longitude": lead.get("longitude")
        },
        "digital_footprints": {
            "gmaps_rating": lead.get("rating"),
            "gmaps_reviews_count": lead.get("reviews_count", 0)
        },
        "commercial_intelligence": {
            "lead_score": lead.get("lead_score", 0),
            "priority_tier": lead.get("priority_tier", "Tier D"),
            "recommended_products": lead.get("recommended_products", "")
        },
        "outreach_logs": {
            "outreach_status": "Belum Dihubungi",
            "whatsapp_pitch": lead.get("whatsapp_pitch", "")
        }
    }
    try:
        upsert_lead_sqlite(entity_payload, db_path=str(LEADS_DB))
    except Exception as e:
        print(f"Gagal menyimpan ke entitas SQLite: {e}")

    return True


def run_radius_scraper(
    limit: Optional[int] = None,
    dry_run: bool = False,
    radius: Optional[int] = None,
    sector: Optional[str] = None,
    notify_telegram: bool = True
) -> List[Dict[str, Any]]:
    init_db()

    state = load_state()
    center_lat = state.get("center_lat", LAT_ORIGIN)
    center_lon = state.get("center_lon", LON_ORIGIN)
    current_radius_km = radius or state.get("current_radius_km", 1)
    current_sector_index = state.get("current_sector_index", 0)
    completed_sectors = state.get("completed_sectors_in_radius", [])
    seen_place_ids = set(state.get("seen_place_ids", []))

    sector_keys = [sector] if sector and sector in SECTOR_QUERIES else list(SECTOR_QUERIES.keys())
    total_new_leads: List[Dict[str, Any]] = []

    zoom_map = {1: 16, 2: 15, 3: 14, 4: 14, 5: 13}
    zoom = zoom_map.get(current_radius_km, 13)

    print(f"Memulai perayapan radius dari ({center_lat}, {center_lon})")
    print(f"Radius aktif: {current_radius_km} km | Zoom: {zoom}z")

    max_loops = 1 if dry_run else len(sector_keys)
    loop_count = 0

    while loop_count < max_loops:
        loop_count += 1
        if current_sector_index >= len(sector_keys):
            print(f"Seluruh sektor telah selesai dipindai untuk radius {current_radius_km} km.")
            current_radius_km += 1
            current_sector_index = 0
            completed_sectors = []
            zoom = zoom_map.get(current_radius_km, 13)
            print(f"Memperluas pencarian ke radius {current_radius_km} km (Zoom: {zoom}z)...")
            if dry_run:
                break

        sector_key = sector_keys[current_sector_index]

        if sector_key in completed_sectors and not sector:
            current_sector_index += 1
            continue

        queries = SECTOR_QUERIES[sector_key]
        print(f"\nMemindai sektor: {sector_key} (Radius {current_radius_km} km)")

        new_places_in_sector = 0

        for q in queries:
            full_query = f"{q} Makassar"
            print(f"  Pencarian query: '{full_query}'")
            places = search_places(
                query=full_query,
                city="Makassar",
                limit=limit or 5,
                dry_run=dry_run,
                lat=center_lat,
                lon=center_lon,
                zoom=zoom
            )

            for p in places:
                p_id = p.get("place_id") or p.get("google_maps_place_id")
                if p_id and p_id in seen_place_ids:
                    continue

                lead = process_place(p, None, center_lat, center_lon, sector_key)
                if not lead:
                    continue

                dist = lead["distance_km"]
                if dist > current_radius_km:
                    continue

                if save_lead(lead, dry_run=dry_run):
                    if p_id:
                        seen_place_ids.add(p_id)
                    new_places_in_sector += 1
                    total_new_leads.append(lead)
                    print(f"    [+] {lead['business_name']} | WA: {lead.get('whatsapp') or '-'} | Jarak: {dist} km")

                if limit and len(total_new_leads) >= limit:
                    break

            if limit and len(total_new_leads) >= limit:
                break

        completed_sectors.append(sector_key)
        current_sector_index += 1

        if not dry_run:
            state["current_radius_km"] = current_radius_km
            state["current_sector_index"] = current_sector_index
            state["completed_sectors_in_radius"] = completed_sectors
            state["seen_place_ids"] = list(seen_place_ids)
            state["last_scraped_at"] = datetime.utcnow().isoformat()
            save_state(state)

        if limit and len(total_new_leads) >= limit:
            print(f"Batas target tercapai: {len(total_new_leads)} prospek baru.")
            break

        if sector:
            break

    # Otomatis kirim ke Google Spreadsheet (Hanya Spreadsheet, tanpa file CSV)
    if total_new_leads and not dry_run:
        print(f"Menyinkronkan {len(total_new_leads)} prospek baru ke Google Spreadsheet 'Radar Prospek'...")
        sync_leads_to_hermes(leads=total_new_leads, sheet_name="Radar Prospek", clear_first=False, dry_run=False)

    return total_new_leads


def main():
    parser = argparse.ArgumentParser(description="Perayap Google Maps berbasis radius bertingkat RUANG VISUAL")
    parser.add_argument("--limit", type=int, default=5, help="Batas maksimal tempat yang dirayap")
    parser.add_argument("--radius", type=int, default=None, help="Paksa radius tertentu dalam km")
    parser.add_argument("--sector", type=str, default=None, help="Pilih sektor tertentu (fnb_hospitality, dll)")
    parser.add_argument("--dry-run", action="store_true", help="Simulasi tanpa menyimpan ke database")

    args = parser.parse_args()

    try:
        run_radius_scraper(
            limit=args.limit,
            dry_run=args.dry_run,
            radius=args.radius,
            sector=args.sector
        )
    except KeyboardInterrupt:
        print("\nPerayapan dihentikan pengguna.")
    except Exception as e:
        print(f"Galat perayapan: {e}")
        raise


if __name__ == "__main__":
    main()
