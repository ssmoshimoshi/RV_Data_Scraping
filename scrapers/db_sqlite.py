import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List


DB_PATH = PROJECT_ROOT / 'data' / 'leads.sqlite'

DDL_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    business_name TEXT NOT NULL,
    target_sector TEXT NOT NULL,
    primary_service_pillar TEXT NOT NULL,
    category_raw TEXT,
    whatsapp_number TEXT,
    phone_raw TEXT,
    is_wa_valid INTEGER DEFAULT 0,
    is_commercial INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS locations (
    entity_id TEXT PRIMARY KEY,
    place_id TEXT,
    address_full TEXT,
    district_area TEXT,
    city TEXT DEFAULT 'makassar',
    sales_cluster TEXT,
    latitude REAL,
    longitude REAL,
    opening_hours_json TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS digital_footprints (
    entity_id TEXT PRIMARY KEY,
    website_url TEXT,
    gmaps_rating REAL,
    gmaps_reviews_count INTEGER DEFAULT 0,
    review_snippets_json TEXT,
    instagram_handle TEXT,
    instagram_bio TEXT,
    instagram_followers INTEGER DEFAULT 0,
    latest_post_date TEXT,
    tiktok_handle TEXT,
    has_meta_ads INTEGER DEFAULT 0,
    meta_ads_data_json TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS commercial_intelligence (
    entity_id TEXT PRIMARY KEY,
    lead_score INTEGER DEFAULT 0,
    priority_tier TEXT DEFAULT 'Tier D',
    score_legitimacy INTEGER DEFAULT 0,
    score_velocity INTEGER DEFAULT 0,
    score_turnover INTEGER DEFAULT 0,
    score_budget INTEGER DEFAULT 0,
    detected_service_needs TEXT,
    service_pain_points TEXT,
    est_order_value_idr INTEGER DEFAULT 0,
    recommended_products TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS channel_posts (
    post_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    caption TEXT,
    posted_at TEXT,
    engagement_rate REAL DEFAULT 0.0,
    service_trigger_signal TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS outreach_logs (
    entity_id TEXT PRIMARY KEY,
    outreach_status TEXT DEFAULT 'Belum Dihubungi',
    whatsapp_pitch TEXT,
    sales_notes TEXT,
    contacted_at TEXT,
    last_followup_at TEXT,
    sales_rep_name TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entities_sector ON entities(target_sector);
CREATE INDEX IF NOT EXISTS idx_entities_pillar ON entities(primary_service_pillar);
CREATE INDEX IF NOT EXISTS idx_intelligence_tier ON commercial_intelligence(priority_tier);
CREATE INDEX IF NOT EXISTS idx_intelligence_score ON commercial_intelligence(lead_score);
CREATE INDEX IF NOT EXISTS idx_locations_cluster ON locations(sales_cluster);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_logs(outreach_status);
"""


def init_db(db_path: Optional[Path] = None) -> bool:
    db = db_path or DB_PATH
    db.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        conn = sqlite3.connect(str(db))
        cursor = conn.cursor()
        for stmt in DDL_SCHEMA.split(';'):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        raise RuntimeError(f"init_db failed: {e}")


def upsert_lead(entity_data: Dict[str, Any], db_path: Optional[Path] = None) -> bool:
    db = db_path or DB_PATH
    
    try:
        conn = sqlite3.connect(str(db))
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()
        
        entity_id = entity_data.get('entity_id')
        if not entity_id:
            raise ValueError("entity_id is required")

        now_iso = datetime.now().isoformat()

        cursor.execute(
            '''
            INSERT INTO entities (
                entity_id, business_name, target_sector, primary_service_pillar,
                category_raw, whatsapp_number, phone_raw, is_wa_valid, is_commercial,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                business_name = excluded.business_name,
                target_sector = excluded.target_sector,
                primary_service_pillar = excluded.primary_service_pillar,
                category_raw = excluded.category_raw,
                whatsapp_number = COALESCE(excluded.whatsapp_number, entities.whatsapp_number),
                phone_raw = COALESCE(excluded.phone_raw, entities.phone_raw),
                is_wa_valid = MAX(entities.is_wa_valid, excluded.is_wa_valid),
                is_commercial = excluded.is_commercial,
                updated_at = excluded.updated_at
            ''',
            (
                entity_id,
                entity_data.get('business_name', ''),
                entity_data.get('target_sector', ''),
                entity_data.get('primary_service_pillar', ''),
                entity_data.get('category_raw'),
                entity_data.get('whatsapp_number'),
                entity_data.get('phone_raw'),
                int(entity_data.get('is_wa_valid', 0)),
                int(entity_data.get('is_commercial', 1)),
                now_iso,
                now_iso,
            )
        )

        locations_data = entity_data.get('locations') or {}
        cursor.execute(
            '''
            INSERT INTO locations (
                entity_id, place_id, address_full, district_area, city,
                sales_cluster, latitude, longitude, opening_hours_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                place_id = COALESCE(excluded.place_id, locations.place_id),
                address_full = COALESCE(excluded.address_full, locations.address_full),
                district_area = COALESCE(excluded.district_area, locations.district_area),
                city = COALESCE(excluded.city, locations.city),
                sales_cluster = COALESCE(excluded.sales_cluster, locations.sales_cluster),
                latitude = COALESCE(excluded.latitude, locations.latitude),
                longitude = COALESCE(excluded.longitude, locations.longitude),
                opening_hours_json = COALESCE(excluded.opening_hours_json, locations.opening_hours_json)
            ''',
            (
                entity_id,
                locations_data.get('place_id'),
                locations_data.get('address_full'),
                locations_data.get('district_area'),
                locations_data.get('city', 'makassar'),
                locations_data.get('sales_cluster'),
                locations_data.get('latitude'),
                locations_data.get('longitude'),
                json.dumps(locations_data.get('opening_hours_json', {})) if locations_data.get('opening_hours_json') else None,
            )
        )

        digital_data = entity_data.get('digital_footprints') or {}
        cursor.execute(
            '''
            INSERT INTO digital_footprints (
                entity_id, website_url, gmaps_rating, gmaps_reviews_count, review_snippets_json,
                instagram_handle, instagram_bio, instagram_followers, latest_post_date,
                tiktok_handle, has_meta_ads, meta_ads_data_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                website_url = COALESCE(excluded.website_url, digital_footprints.website_url),
                gmaps_rating = COALESCE(excluded.gmaps_rating, digital_footprints.gmaps_rating),
                gmaps_reviews_count = MAX(digital_footprints.gmaps_reviews_count, excluded.gmaps_reviews_count),
                review_snippets_json = COALESCE(excluded.review_snippets_json, digital_footprints.review_snippets_json),
                instagram_handle = COALESCE(excluded.instagram_handle, digital_footprints.instagram_handle),
                instagram_bio = COALESCE(excluded.instagram_bio, digital_footprints.instagram_bio),
                instagram_followers = MAX(digital_footprints.instagram_followers, excluded.instagram_followers),
                latest_post_date = COALESCE(excluded.latest_post_date, digital_footprints.latest_post_date),
                tiktok_handle = COALESCE(excluded.tiktok_handle, digital_footprints.tiktok_handle),
                has_meta_ads = MAX(digital_footprints.has_meta_ads, excluded.has_meta_ads),
                meta_ads_data_json = COALESCE(excluded.meta_ads_data_json, digital_footprints.meta_ads_data_json)
            ''',
            (
                entity_id,
                digital_data.get('website_url'),
                digital_data.get('gmaps_rating'),
                digital_data.get('gmaps_reviews_count', 0),
                json.dumps(digital_data.get('review_snippets_json', [])) if digital_data.get('review_snippets_json') else None,
                digital_data.get('instagram_handle'),
                digital_data.get('instagram_bio'),
                digital_data.get('instagram_followers', 0),
                digital_data.get('latest_post_date'),
                digital_data.get('tiktok_handle'),
                int(digital_data.get('has_meta_ads', 0)),
                json.dumps(digital_data.get('meta_ads_data_json', {})) if digital_data.get('meta_ads_data_json') else None,
            )
        )

        intel_data = entity_data.get('commercial_intelligence') or {}
        cursor.execute(
            '''
            INSERT INTO commercial_intelligence (
                entity_id, lead_score, priority_tier, score_legitimacy, score_velocity,
                score_turnover, score_budget, detected_service_needs, service_pain_points,
                est_order_value_idr, recommended_products
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                lead_score = excluded.lead_score,
                priority_tier = excluded.priority_tier,
                score_legitimacy = excluded.score_legitimacy,
                score_velocity = excluded.score_velocity,
                score_turnover = excluded.score_turnover,
                score_budget = excluded.score_budget,
                detected_service_needs = COALESCE(excluded.detected_service_needs, commercial_intelligence.detected_service_needs),
                service_pain_points = COALESCE(excluded.service_pain_points, commercial_intelligence.service_pain_points),
                est_order_value_idr = COALESCE(excluded.est_order_value_idr, commercial_intelligence.est_order_value_idr),
                recommended_products = COALESCE(excluded.recommended_products, commercial_intelligence.recommended_products)
            ''',
            (
                entity_id,
                intel_data.get('lead_score', 0),
                intel_data.get('priority_tier', 'Tier D'),
                intel_data.get('score_legitimacy', 0),
                intel_data.get('score_velocity', 0),
                intel_data.get('score_turnover', 0),
                intel_data.get('score_budget', 0),
                json.dumps(intel_data.get('detected_service_needs', [])) if intel_data.get('detected_service_needs') else None,
                json.dumps(intel_data.get('service_pain_points', [])) if intel_data.get('service_pain_points') else None,
                intel_data.get('est_order_value_idr', 0),
                intel_data.get('recommended_products'),
            )
        )

        outreach_data = entity_data.get('outreach_logs') or {}
        cursor.execute(
            '''
            INSERT INTO outreach_logs (
                entity_id, outreach_status, whatsapp_pitch, sales_notes,
                contacted_at, last_followup_at, sales_rep_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                whatsapp_pitch = COALESCE(NULLIF(excluded.whatsapp_pitch, ''), outreach_logs.whatsapp_pitch),
                outreach_status = CASE 
                    WHEN excluded.outreach_status IS NOT NULL AND excluded.outreach_status != 'Belum Dihubungi'
                    THEN excluded.outreach_status
                    ELSE outreach_logs.outreach_status 
                END,
                sales_notes = CASE 
                    WHEN excluded.sales_notes IS NOT NULL AND excluded.sales_notes != ''
                    THEN excluded.sales_notes
                    ELSE outreach_logs.sales_notes 
                END,
                contacted_at = COALESCE(excluded.contacted_at, outreach_logs.contacted_at),
                last_followup_at = COALESCE(excluded.last_followup_at, outreach_logs.last_followup_at),
                sales_rep_name = COALESCE(excluded.sales_rep_name, outreach_logs.sales_rep_name)
            ''',
            (
                entity_id,
                outreach_data.get('outreach_status', 'Belum Dihubungi'),
                outreach_data.get('whatsapp_pitch'),
                outreach_data.get('sales_notes'),
                outreach_data.get('contacted_at'),
                outreach_data.get('last_followup_at'),
                outreach_data.get('sales_rep_name'),
            )
        )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        raise RuntimeError(f"upsert_lead failed: {e}")


def get_all_leads(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    db = db_path or DB_PATH
    
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                e.entity_id, e.business_name, e.target_sector, e.primary_service_pillar,
                e.category_raw, e.whatsapp_number, e.phone_raw, e.is_wa_valid, e.is_commercial,
                l.place_id, l.address_full, l.district_area, l.city, l.sales_cluster,
                l.latitude, l.longitude, l.opening_hours_json,
                df.website_url, df.gmaps_rating, df.gmaps_reviews_count, df.review_snippets_json,
                df.instagram_handle, df.instagram_bio, df.instagram_followers,
                df.latest_post_date, df.tiktok_handle, df.has_meta_ads, df.meta_ads_data_json,
                ci.lead_score, ci.priority_tier, ci.score_legitimacy, ci.score_velocity,
                ci.score_turnover, ci.score_budget, ci.detected_service_needs,
                ci.service_pain_points, ci.est_order_value_idr, ci.recommended_products,
                ol.outreach_status, ol.whatsapp_pitch, ol.sales_notes, ol.contacted_at,
                ol.last_followup_at, ol.sales_rep_name
            FROM entities e
            LEFT JOIN locations l ON e.entity_id = l.entity_id
            LEFT JOIN digital_footprints df ON e.entity_id = df.entity_id
            LEFT JOIN commercial_intelligence ci ON e.entity_id = ci.entity_id
            LEFT JOIN outreach_logs ol ON e.entity_id = ol.entity_id
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            row_dict = dict(row)
            if row_dict.get('review_snippets_json'):
                row_dict['review_snippets_json'] = json.loads(row_dict['review_snippets_json'])
            if row_dict.get('opening_hours_json'):
                row_dict['opening_hours_json'] = json.loads(row_dict['opening_hours_json'])
            if row_dict.get('meta_ads_data_json'):
                row_dict['meta_ads_data_json'] = json.loads(row_dict['meta_ads_data_json'])
            if row_dict.get('detected_service_needs'):
                row_dict['detected_service_needs'] = json.loads(row_dict['detected_service_needs'])
            if row_dict.get('service_pain_points'):
                row_dict['service_pain_points'] = json.loads(row_dict['service_pain_points'])
            result.append(row_dict)
        
        return result
    except Exception as e:
        raise RuntimeError(f"get_all_leads failed: {e}")

def update_outreach_log(entity_id: str, status: str, notes: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO outreach_logs (entity_id, outreach_status, sales_notes, contacted_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
            outreach_status = excluded.outreach_status,
            sales_notes = excluded.sales_notes,
            contacted_at = excluded.contacted_at
        """, (entity_id, status, notes, datetime.now().isoformat()))
        conn.commit()


def seed_sample_leads_to_sqlite(db_path: Optional[Path] = None) -> int:
    """Mengisi database SQLite lokal dengan prospek terverifikasi dari SAMPLE_LEADS."""
    from scrapers.content_inspector import save_inspected_posts_to_sqlite
    from scrapers.dashboard_server import enrich_lead_card
    from scrapers.outreach_generator import _resolve_sector
    from scrapers.route_cluster import assign_sales_cluster
    from scrapers.sample_leads import SAMPLE_LEADS

    init_db(db_path)
    db = db_path or DB_PATH
    saved_count = 0

    for lead in SAMPLE_LEADS:
        enriched = enrich_lead_card(lead)
        sector = _resolve_sector(lead.get("category", "fnb"))
        cluster = assign_sales_cluster(lead.get("address_full", ""), lead.get("city", ""))

        entity_data = {
            "entity_id": lead["id"],
            "business_name": lead["business_name"],
            "target_sector": sector,
            "primary_service_pillar": enriched.get("primary_service_pillar") or "packaging",
            "category_raw": lead.get("category"),
            "whatsapp_number": lead.get("whatsapp_number"),
            "phone_raw": lead.get("phone_number"),
            "is_wa_valid": 1 if lead.get("whatsapp_number") else 0,
            "is_commercial": 1,
            "locations": {
                "place_id": lead.get("google_maps_place_id"),
                "address_full": lead.get("address_full"),
                "district_area": lead.get("city"),
                "city": lead.get("city", "Makassar"),
                "sales_cluster": cluster,
                "latitude": lead.get("latitude"),
                "longitude": lead.get("longitude"),
            },
            "digital_footprints": {
                "website_url": lead.get("external_website_url"),
                "gmaps_rating": lead.get("rating"),
                "gmaps_reviews_count": lead.get("reviews_count", 0),
                "instagram_handle": (lead.get("channels") or {}).get("instagram"),
                "tiktok_handle": (lead.get("channels") or {}).get("tiktok"),
                "latest_post_date": lead.get("latest_post_date"),
                "has_meta_ads": 1 if lead.get("is_ad_active") else 0,
            },
            "commercial_intelligence": {
                "lead_score": enriched.get("lead_score", 0),
                "priority_tier": enriched.get("priority_tier", "Tier B"),
                "score_legitimacy": enriched.get("score_legitimacy", 0),
                "score_velocity": enriched.get("score_velocity", 0),
                "score_turnover": enriched.get("score_turnover", 0),
                "score_budget": enriched.get("score_budget", 0),
                "detected_service_needs": enriched.get("detected_service_needs", []),
                "service_pain_points": enriched.get("packaging_pain_points", []),
                "est_order_value_idr": (enriched.get("estimated_commercials") or {}).get("est_monthly_value_min_idr", 0),
                "recommended_products": ", ".join(enriched.get("recommended_products", [])),
            },
            "outreach_logs": {
                "outreach_status": lead.get("status", "ready_to_pitch"),
                "whatsapp_pitch": enriched.get("pitch_text", ""),
            },
        }

        if upsert_lead(entity_data, db):
            saved_count += 1
            if lead.get("top_posts"):
                plat = lead.get("platform") or "instagram"
                save_inspected_posts_to_sqlite(lead["id"], plat, lead["top_posts"], db_path=db)

    return saved_count

