import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import http.server
import socketserver
import sqlite3
import threading
import time
import urllib.parse
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from scrapers.lead_scoring import (
    classify_category,
    calculate_score,
    calculate_4_pillars_score,
    infer_product_needs,
    generate_whatsapp_pitch,
    estimate_packaging_volume_and_value,
)
from scrapers.db_sqlite import get_all_leads as get_all_leads_from_sqlite, update_outreach_log, update_manual_override
from scrapers.exporter import find_latest_dossier
from scrapers.content_inspector import (
    fetch_social_top_posts,
    save_inspected_posts_to_sqlite,
    clean_social_handle
)

PORT = 3000

SAMPLE_LEADS = []


def get_leads_table_data() -> list:
    db_path = PROJECT_ROOT / 'data' / 'leads.sqlite'
    if not db_path.exists():
        return []
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
        if not cursor.fetchone():
            conn.close()
            return []
        
        cursor.execute("""
            SELECT * FROM leads 
            WHERE status != 'dropped' OR status IS NULL
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        leads = []
        for row in rows:
            lead = dict(row)
            lead['id'] = lead.get('lead_id', f"lead-{len(leads)}")
            lead['entity_id'] = lead.get('lead_id', '')
            leads.append(lead)
        
        return leads
    except Exception as e:
        print(f"Error reading leads table: {e}")
        return []


_DEVICE_STATUS_CACHE: Dict[str, Any] = {
    "data": None,
    "timestamp": 0.0
}


def check_android_device_status() -> dict:
    global _DEVICE_STATUS_CACHE
    now = time.time()
    if _DEVICE_STATUS_CACHE["data"] is not None and (now - _DEVICE_STATUS_CACHE["timestamp"]) < 20.0:
        return _DEVICE_STATUS_CACHE["data"]

    # Pemeriksaan cepat via CLI adb devices untuk mencegah timeout blocking 10 detik jika perangkat tidak terhubung
    try:
        import subprocess
        adb_exec = "/Users/muhammadfanani/Library/Android/sdk/platform-tools/adb"
        cmd = [adb_exec if Path(adb_exec).exists() else "adb", "devices"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=0.8)
        lines = [line.strip() for line in proc.stdout.strip().split("\n") if line.strip()]
        attached = [l.split()[0] for l in lines[1:] if "\tdevice" in l]

        if not attached:
            result = {
                "connected": False,
                "device_model": "Xiaomi Redmi Note 14 5G",
                "serial": None,
                "message": "Tidak ada perangkat Android terhubung via USB"
            }
            _DEVICE_STATUS_CACHE = {"data": result, "timestamp": now}
            return result
    except Exception:
        pass

    try:
        from scrapers.android_scraper import get_android_device, ensure_device_ready

        device = get_android_device()
        if device and ensure_device_ready(device):
            serial = device.serial if hasattr(device, "serial") else "unknown"
            result = {
                "connected": True,
                "device_model": "Xiaomi Redmi Note 14 5G",
                "serial": serial
            }
        else:
            result = {
                "connected": False,
                "device_model": "Xiaomi Redmi Note 14 5G",
                "serial": None
            }
    except Exception as e:
        result = {
            "connected": False,
            "device_model": "Xiaomi Redmi Note 14 5G",
            "serial": None,
            "error": str(e)
        }

    _DEVICE_STATUS_CACHE = {"data": result, "timestamp": now}
    return result


def update_lead_status_in_db(lead_id: str, status: str, reason: str = '') -> bool:
    db_path = PROJECT_ROOT / 'data' / 'leads.sqlite'
    if not db_path.exists():
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
        if not cursor.fetchone():
            conn.close()
            return False
        
        cursor.execute("PRAGMA table_info(leads)")
        cols = [c[1] for c in cursor.fetchall()]
        id_col = "place_id" if "place_id" in cols and "lead_id" not in cols else "lead_id"
        notes_clause = ", notes = ?" if "notes" in cols else ""
        updated_clause = ", updated_at = CURRENT_TIMESTAMP" if "updated_at" in cols else ""
        
        notes_text = f"Status changed to {status}"
        if reason:
            notes_text += f". Reason: {reason}"
        
        params = [status]
        if "notes" in cols:
            params.append(notes_text)
        params.append(lead_id)

        cursor.execute(f"""
            UPDATE leads 
            SET status = ?{notes_clause}{updated_clause}
            WHERE {id_col} = ?
        """, params)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    except Exception as e:
        print(f"Error updating lead status: {e}")
        return False


def inspect_account_content(platform: str, handle_or_url: str, business_name: str = "", force_refresh: bool = False, dry_run: bool = False) -> dict:
    return fetch_social_top_posts(
        platform=platform,
        handle_or_url=handle_or_url,
        business_name=business_name,
        limit=5,
        force_refresh=force_refresh,
        dry_run=dry_run
    )


def enrich_lead_card(lead: dict) -> dict:
    enriched = dict(lead)
    category = enriched.get("category") or classify_category(enriched.get("business_name", ""), "", [])
    enriched["category"] = category
    
    four_pillars = calculate_4_pillars_score(enriched)
    enriched["score_legitimacy"] = enriched.get("score_legitimacy") if enriched.get("score_legitimacy") is not None else four_pillars["score_legitimacy"]
    enriched["score_velocity"] = enriched.get("score_velocity") if enriched.get("score_velocity") is not None else four_pillars["score_velocity"]
    enriched["score_turnover"] = enriched.get("score_turnover") if enriched.get("score_turnover") is not None else four_pillars["score_turnover"]
    enriched["score_budget"] = enriched.get("score_budget") if enriched.get("score_budget") is not None else four_pillars["score_budget"]
    pillars_total = enriched.get("lead_score") if enriched.get("lead_score") is not None else four_pillars["score_total"]
    enriched["pillars_total"] = pillars_total
    enriched["score"] = pillars_total
    enriched["lead_score"] = pillars_total
    enriched["priority_tier"] = enriched.get("priority_tier") or four_pillars["tier"]

    # Penetapan manual tim sales menimpa hasil kalkulasi otomatis
    if enriched.get("is_manual_override"):
        if enriched.get("manual_score") is not None:
            enriched["pillars_total"] = enriched["score"] = enriched["lead_score"] = int(enriched["manual_score"])
        if enriched.get("manual_tier"):
            enriched["priority_tier"] = enriched["manual_tier"]
    enriched["reason_summary"] = enriched.get("reason_summary") or four_pillars["reason_summary"]
    
    needs = infer_product_needs(category, enriched.get("business_name", ""), "")
    enriched["recommended_products"] = needs["recommended_products"]
    enriched["materials_finishing"] = needs["materials_finishing"]
    enriched["value_proposition"] = needs["value_proposition"]
    
    # Estimasi komersial kemasan dan pain points
    if "estimated_commercials" not in enriched or not enriched["estimated_commercials"]:
        enriched["estimated_commercials"] = estimate_packaging_volume_and_value(enriched)

    if "packaging_pain_points" not in enriched:
        enriched["packaging_pain_points"] = []

    pitch_info = generate_whatsapp_pitch(enriched)
    if pitch_info:
        enriched["pitch_text"] = pitch_info["pitch_text"]
        enriched["wa_link"] = pitch_info["wa_link"]
    elif enriched.get("whatsapp_pitch"):
        enriched["pitch_text"] = enriched["whatsapp_pitch"]
        wa_num = enriched.get("whatsapp_number") or ""
        if wa_num:
            import urllib.parse
            enriched["wa_link"] = f"https://wa.me/{wa_num}?text={urllib.parse.quote(enriched['whatsapp_pitch'])}"
        else:
            enriched["wa_link"] = ""
    else:
        enriched["pitch_text"] = ""
        enriched["wa_link"] = ""

    if "channels" not in enriched:
        enriched["channels"] = {
            "google_maps": enriched.get("platform_profile_url", ""),
            "instagram": "",
            "tiktok": "",
            "facebook": "",
            "threads": "",
            "gofood": "",
            "shopeefood": "",
            "grabfood": ""
        }

    if "top_posts" not in enriched:
        enriched["top_posts"] = []
        
    return enriched


def load_raw_scraped_leads() -> list[dict]:
    raw_dir = PROJECT_ROOT / "data" / "raw"
    if not raw_dir.exists():
        return []
    leads = []
    seen_names = set()
    for filepath in sorted(raw_dir.glob("gmaps_places_*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        name = (item.get("title") or "").strip()
                        if not name or name.lower() in seen_names:
                            continue
                        seen_names.add(name.lower())
                        pid = item.get("place_id") or f"scraped-{len(seen_names)}"
                        leads.append({
                            "id": f"gmaps-{pid}",
                            "business_name": name,
                            "category": item.get("category", "fnb_beverage"),
                            "platform": "google_maps",
                            "google_maps_place_id": item.get("place_id"),
                            "rating": item.get("total_score") or item.get("rating", 4.5),
                            "reviews_count": item.get("reviews_count", 0),
                            "latitude": item.get("latitude"),
                            "longitude": item.get("longitude"),
                            "city": item.get("city", "Makassar"),
                            "address_full": item.get("address", ""),
                            "whatsapp_number": item.get("whatsapp_number", ""),
                            "phone_number": item.get("phone_number", ""),
                            "follower_count": item.get("follower_count", item.get("reviews_count", 0) * 10),
                            "is_active_verified": True,
                            "is_ad_active": False,
                            "external_website_url": item.get("website", ""),
                            "latest_post_date": (datetime.now() - timedelta(days=2)).isoformat(),
                            "status": "ready_to_pitch" if item.get("whatsapp_number") else "new_lead",
                            "packaging_pain_points": item.get("packaging_pain_points", []),
                            "estimated_commercials": item.get("estimated_commercials", {}),
                            "channels": {
                                "google_maps": f"https://www.google.com/maps/place/?q=place_id:{item.get('place_id')}" if item.get("place_id") else "",
                                "instagram": item.get("website", "") if "instagram.com" in (item.get("website") or "") else "",
                                "tiktok": "",
                                "threads": "",
                                "food_delivery": ""
                            }
                        })
        except Exception:
            continue
    return leads


_FOOD_DELIVERY_PLATFORMS = {"gofood": "GoFood", "grabfood": "GrabFood", "shopeefood": "ShopeeFood"}
_CHANNEL_URL_KEYS = ("website", "external_website_url", "profile_url", "platform_profile_url", "url")


def build_channels_from_records(ent: dict, records: list, first_rec: dict) -> dict:
    place_id = ent.get("place_id") or first_rec.get("place_id") or first_rec.get("google_maps_place_id")
    if place_id:
        google_maps = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    else:
        website = ent.get("external_website_url") or first_rec.get("website") or ""
        google_maps = website if "google.com/maps" in website.lower() else ""

    instagram = ""
    tiktok = ""
    threads = ""
    food_links = []
    food_names = []
    for rec in records:
        platform = str(rec.get("platform", "")).lower()
        for key in _CHANNEL_URL_KEYS:
            val = str(rec.get(key) or "")
            if not val:
                continue
            low = val.lower()
            if "instagram.com" in low and not instagram:
                instagram = val
            elif "tiktok.com" in low and not tiktok:
                tiktok = val
            elif "threads.net" in low and not threads:
                threads = val
        handle = rec.get("platform_handle") or rec.get("username") or ""
        if platform == "tiktok" and not tiktok:
            tiktok = f"https://www.tiktok.com/@{handle}" if handle else platform
        if platform == "threads" and not threads:
            threads = f"https://www.threads.net/@{handle}" if handle else platform
        if platform in _FOOD_DELIVERY_PLATFORMS:
            link = rec.get("url") or rec.get("merchant_url") or ""
            if link:
                food_links.append(link)
            food_names.append(_FOOD_DELIVERY_PLATFORMS[platform])

    food_delivery = food_links[0] if food_links else ", ".join(dict.fromkeys(food_names))
    return {
        "google_maps": google_maps,
        "instagram": instagram,
        "tiktok": tiktok,
        "threads": threads,
        "food_delivery": food_delivery,
    }


def load_processed_dossiers(processed_dir=PROJECT_ROOT / "data" / "processed") -> list[dict]:
    path = find_latest_dossier(processed_dir)
    if not path:
        return []
    try:
        entities = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(entities, list):
        return []

    leads = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        records = [r for r in ent.get("records") or [] if isinstance(r, dict)]
        first_rec = records[0] if records else {}
        est = ent.get("estimated_commercials") or next(
            (r.get("estimated_commercials") for r in records if r.get("estimated_commercials")), {})
        pain_points = ent.get("packaging_pain_points") or next(
            (r.get("packaging_pain_points") for r in records if r.get("packaging_pain_points")), [])
        channels = ent.get("channels") or build_channels_from_records(ent, records, first_rec)
        rating = ent.get("rating") or first_rec.get("total_score") or first_rec.get("rating") or 4.5
        reviews_count = ent.get("reviews_count") or first_rec.get("reviews_count") or 0
        place_id = first_rec.get("place_id") or ""
        leads.append({
            "id": ent.get("entity_id") or f"dossier-{len(leads) + 1}",
            "entity_id": ent.get("entity_id", ""),
            "business_name": ent.get("business_name", ""),
            "category": ent.get("category") or first_rec.get("category", ""),
            "platforms": ent.get("platforms", []),
            "city": ent.get("city", ""),
            "district_area": ent.get("district_area", ""),
            "address_full": first_rec.get("address") or first_rec.get("address_full", ""),
            "latitude": first_rec.get("latitude"),
            "longitude": first_rec.get("longitude"),
            "rating": rating,
            "reviews_count": reviews_count,
            "google_maps_place_id": place_id,
            "whatsapp_number": ent.get("whatsapp_number", ""),
            "phone_number": first_rec.get("phone_number", ""),
            "external_website_url": first_rec.get("website") or first_rec.get("external_website_url", ""),
            "lead_score": ent.get("lead_score"),
            "priority_tier": ent.get("priority_tier", ""),
            "estimated_commercials": est,
            "packaging_pain_points": pain_points,
            "channels": channels,
            "top_posts": ent.get("top_posts") or first_rec.get("top_posts") or [],
            "whatsapp_pitch": ent.get("whatsapp_pitch", ""),
            "is_active_verified": bool(ent.get("whatsapp_number")),
            "status": "ready_to_pitch" if ent.get("whatsapp_number") else "new_lead",
            "outreach_status": ent.get("outreach_status") or "Belum Dihubungi",
            "outreach_notes": ent.get("outreach_notes") or "",
            "contacted_at": ent.get("contacted_at"),
            "manual_tier": ent.get("manual_tier") or "",
            "manual_score": ent.get("manual_score"),
            "manual_notes": ent.get("manual_notes") or "",
            "is_manual_override": bool(ent.get("is_manual_override")),
        })
    return leads


VALID_OUTREACH_STATUSES = (
    "Belum Dihubungi",
    "Dihubungi",
    "Tertarik",
    "Closing",
    "Tidak Relevan",
    "dropped",
    "new",
    "contacted",
    "converted",
)

VALID_OVERRIDE_TIERS = ("Tier A", "Tier B", "Tier C", "Tier D")


def persist_manual_override_to_dossier(entity_id: str, manual_tier: str, manual_score,
                                       manual_notes: str, is_override: bool,
                                       processed_dir=None) -> bool:
    if processed_dir is None:
        processed_dir = PROJECT_ROOT / "data" / "processed"
    path = find_latest_dossier(processed_dir)
    if not path:
        return False
    try:
        entities = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(entities, list):
        return False
    for ent in entities:
        if not isinstance(ent, dict) or ent.get("entity_id") != entity_id:
            continue
        ent["manual_tier"] = manual_tier
        ent["manual_score"] = manual_score
        ent["manual_notes"] = manual_notes
        ent["is_manual_override"] = is_override
        try:
            path.write_text(json.dumps(entities, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            return False
        return True
    return False


def persist_status_to_dossier(entity_id: str, status: str, notes: str = "",
                              processed_dir=None) -> bool:
    if processed_dir is None:
        processed_dir = PROJECT_ROOT / "data" / "processed"
    path = find_latest_dossier(processed_dir)
    if not path:
        return False
    try:
        entities = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(entities, list):
        return False
    for ent in entities:
        if not isinstance(ent, dict) or ent.get("entity_id") != entity_id:
            continue
        ent["outreach_status"] = status
        ent["outreach_notes"] = notes
        if status in ("Dihubungi", "Closing"):
            ent["contacted_at"] = datetime.now().isoformat()
        try:
            path.write_text(json.dumps(entities, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            return False
        return True
    return False


def persist_channel_to_dossier(entity_id: str, platform: str, channel_value: str, posts: list,
                               processed_dir=None) -> bool:
    if processed_dir is None:
        processed_dir = PROJECT_ROOT / "data" / "processed"
    path = find_latest_dossier(processed_dir)
    if not path:
        return False
    try:
        entities = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(entities, list):
        return False
    for ent in entities:
        if not isinstance(ent, dict) or ent.get("entity_id") != entity_id:
            continue
        channels = ent.get("channels") or {}
        channels[platform] = channel_value
        ent["channels"] = channels
        ent["top_posts"] = posts
        ent["latest_post_date"] = (datetime.now() - timedelta(days=1)).isoformat()
        ent["is_active_verified"] = True
        try:
            path.write_text(json.dumps(entities, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            return False
        return True
    return False


def adapt_sqlite_lead_for_dashboard(item: dict) -> dict:
    entity_id = item.get("entity_id") or ""
    cat = item.get("category_raw") or item.get("target_sector") or "general_commercial"
    place_id = item.get("place_id") or ""
    phone = item.get("phone_raw") or ""
    wa = item.get("whatsapp_number") or ""
    rating = item.get("gmaps_rating")
    try:
        rating = float(rating) if rating is not None else 4.5
    except (ValueError, TypeError):
        rating = 4.5
    reviews_count = item.get("gmaps_reviews_count") or 0
    web_url = item.get("website_url") or ""
    ig = item.get("instagram_handle") or ""
    tt = item.get("tiktok_handle") or ""

    gmaps_url = ""
    if place_id:
        if str(place_id).startswith("http"):
            gmaps_url = str(place_id)
        elif str(place_id).startswith("ChIJ") or "gmaps_" in str(place_id):
            gmaps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
        else:
            gmaps_url = f"https://maps.google.com/?cid={place_id}"
    elif web_url and "google.com/maps" in web_url.lower():
        gmaps_url = web_url

    food_del = item.get("food_delivery_url") or ""
    threads_h = item.get("threads_handle") or ""
    fb = item.get("facebook_handle") or ""
    gofood = item.get("gofood_url") or (food_del if "gofood" in food_del.lower() else "")
    shopeefood = item.get("shopeefood_url") or (food_del if "shopee" in food_del.lower() else "")
    grabfood = item.get("grabfood_url") or (food_del if "grab" in food_del.lower() else "")

    channels = {
        "google_maps": gmaps_url,
        "instagram": ig,
        "tiktok": tt,
        "facebook": fb,
        "threads": threads_h,
        "gofood": gofood,
        "shopeefood": shopeefood,
        "grabfood": grabfood,
        "food_delivery": food_del,
    }

    active_platforms = []
    if gmaps_url:
        active_platforms.append("google_maps")
    if ig:
        active_platforms.append("instagram")
    if tt:
        active_platforms.append("tiktok")
    if fb:
        active_platforms.append("facebook")
    if threads_h:
        active_platforms.append("threads")
    if gofood:
        active_platforms.append("gofood")
    if shopeefood:
        active_platforms.append("shopeefood")
    if grabfood:
        active_platforms.append("grabfood")
    if not active_platforms:
        active_platforms = ["google_maps"]

    top_posts = []
    if entity_id:
        try:
            import sqlite3
            from scrapers.db_sqlite import DB_PATH
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("""
                    SELECT post_id, platform, caption, posted_at, engagement_rate, service_trigger_signal,
                           COALESCE(views, 0) as views, COALESCE(likes, 0) as likes, COALESCE(comments, 0) as comments, post_url
                    FROM channel_posts
                    WHERE entity_id = ?
                    ORDER BY posted_at DESC
                    LIMIT 5
                """, (entity_id,))
                for row in cur.fetchall():
                    tag_list = [t.strip() for t in (row["service_trigger_signal"] or "").split(",") if t.strip()]
                    top_posts.append({
                        "id": row["post_id"],
                        "platform": row["platform"],
                        "caption": row["caption"] or "",
                        "date": row["posted_at"] or "",
                        "views": int(row["views"] or 0),
                        "likes": int(row["likes"] or 0),
                        "comments": int(row["comments"] or 0),
                        "engagement_rate": row["engagement_rate"] or 0.0,
                        "packaging_signal": bool(tag_list),
                        "tags": tag_list,
                        "url": row["post_url"] or ""
                    })
        except Exception:
            pass

    status = item.get("outreach_status") or "Belum Dihubungi"
    notes = item.get("sales_notes") or ""

    return {
        "id": entity_id,
        "entity_id": entity_id,
        "business_name": item.get("business_name") or "",
        "category": cat,
        "target_sector": item.get("target_sector") or "",
        "primary_service_pillar": item.get("primary_service_pillar") or "",
        "platforms": active_platforms,
        "city": item.get("city") or "Makassar",
        "district_area": item.get("district_area") or "",
        "sales_cluster": item.get("sales_cluster") or "",
        "address_full": item.get("address_full") or "",
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
        "rating": rating,
        "reviews_count": reviews_count,
        "google_maps_place_id": place_id,
        "place_id": place_id,
        "whatsapp_number": wa,
        "phone_number": phone,
        "external_website_url": web_url,
        "website_url": web_url,
        "lead_score": item.get("lead_score"),
        "priority_tier": item.get("priority_tier") or "Tier D",
        "score_legitimacy": item.get("score_legitimacy", 0),
        "score_velocity": item.get("score_velocity", 0),
        "score_turnover": item.get("score_turnover", 0),
        "score_budget": item.get("score_budget", 0),
        "estimated_commercials": {"est_monthly_value_min_idr": item.get("est_order_value_idr") or 0},
        "packaging_pain_points": item.get("service_pain_points") or [],
        "detected_service_needs": item.get("detected_service_needs") or [],
        "recommended_products": item.get("recommended_products") or "",
        "channels": channels,
        "top_posts": top_posts,
        "whatsapp_pitch": item.get("whatsapp_pitch") or "",
        "is_active_verified": bool(item.get("is_wa_valid") or wa),
        "is_ad_active": bool(item.get("has_meta_ads")),
        "has_meta_ads": bool(item.get("has_meta_ads")),
        "status": "ready_to_pitch" if wa else "new_lead",
        "outreach_status": status,
        "outreach_notes": notes,
        "sales_notes": notes,
        "contacted_at": item.get("contacted_at"),
        "manual_tier": item.get("manual_tier") or "",
        "manual_score": item.get("manual_score"),
        "manual_notes": item.get("manual_notes") or "",
        "is_manual_override": bool(item.get("is_manual_override")),
    }


def get_all_leads():
    combined = []
    seen_ids = set()
    
    # 1. Tabel leads (Prioritas Tertinggi - dari lead_engine.py)
    leads_from_table = get_leads_table_data()
    for item in leads_from_table:
        lead_id = item.get('lead_id') or item.get('id')
        if lead_id and lead_id not in seen_ids:
            seen_ids.add(lead_id)
            enriched = enrich_lead_card({
                'id': lead_id,
                'entity_id': lead_id,
                'business_name': item.get('business_name', ''),
                'category': item.get('category', ''),
                'whatsapp_number': item.get('whatsapp', ''),
                'phone_raw': item.get('phone', ''),
                'website_url': item.get('website', ''),
                'address_full': item.get('address', ''),
                'rating': item.get('rating', 0.0),
                'reviews_count': item.get('reviews_count', 0),
                'status': item.get('status', 'new'),
                'instagram_handle': item.get('instagram_handle', ''),
                'score': item.get('score', 0),
                'manual_tier': item.get('manual_tier') or '',
                'manual_score': item.get('manual_score'),
                'manual_notes': item.get('manual_notes') or '',
                'is_manual_override': bool(item.get('is_manual_override')),
                'channels': {
                    'instagram': item.get('instagram_handle', ''),
                    'website': item.get('website', '')
                }
            })
            combined.append(enriched)
    
    # 2. SQLite entities (dari db_sqlite.py)
    leads_sqlite = get_all_leads_from_sqlite()
    for item in leads_sqlite:
        entity_id = item.get('entity_id')
        if entity_id and entity_id not in seen_ids:
            seen_ids.add(entity_id)
            combined.append(enrich_lead_card(adapt_sqlite_lead_for_dashboard(item)))
    
    # 3. Fallback: Processed Dossiers & Raw Scraped (Hanya jika data/leads.sqlite belum ada)
    db_file = PROJECT_ROOT / 'data' / 'leads.sqlite'
    if not combined and not db_file.exists():
        processed = load_processed_dossiers()
        scraped = load_raw_scraped_leads()
        seen_names = {p["business_name"].lower() for p in processed if p.get("business_name")}
        combined = list(processed)
        combined += [s for s in scraped if s["business_name"].lower() not in seen_names]
        
        seen_names = {c["business_name"].lower() for c in combined if c.get("business_name")}
        for sample in SAMPLE_LEADS:
            if sample.get("business_name", "").lower() not in seen_names:
                combined.append(sample)
        
        combined = [enrich_lead_card(item) for item in combined]
    
    return combined



def find_lead_by_id(lead_id: str) -> Optional[dict]:
    if not lead_id:
        return None
    for item in get_all_leads():
        if item.get("entity_id") == lead_id or item.get("id") == lead_id or item.get("place_id") == lead_id:
            if "channels" in item and "business_name" in item:
                return item
            return adapt_sqlite_lead_for_dashboard(item)
    for lead in load_processed_dossiers():
        if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
            return lead
    for lead in SAMPLE_LEADS:
        if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
            return lead
    return None


def get_inspector_quick_targets() -> list:
    all_leads = get_all_leads()
    targets = []
    seen_handles = set()

    for lead in all_leads:
        channels = lead.get("channels") or {}
        ig = clean_social_handle(channels.get("instagram") or "")
        tt = clean_social_handle(channels.get("tiktok") or "")
        biz_name = lead.get("business_name") or ""
        cat = lead.get("category") or "general_commercial"
        lead_id = lead.get("id") or lead.get("entity_id") or ""
        dist = lead.get("district_area") or "Makassar"

        if ig and ig not in seen_handles:
            seen_handles.add(ig)
            targets.append({
                "lead_id": lead_id,
                "business_name": biz_name,
                "platform": "instagram",
                "handle": f"@{ig}",
                "category": cat,
                "followers_count": lead.get("followers_count") or 18500,
                "district_area": dist
            })

        if tt and tt not in seen_handles:
            seen_handles.add(tt)
            targets.append({
                "lead_id": lead_id,
                "business_name": biz_name,
                "platform": "tiktok",
                "handle": f"@{tt}",
                "category": cat,
                "followers_count": lead.get("followers_count") or 12000,
                "district_area": dist
            })

        if len(targets) >= 8:
            break

    defaults = [
        {"lead_id": "lead-001", "business_name": "Kopi Titik Temu Pengayoman", "platform": "instagram", "handle": "@titiktemumks", "category": "fnb_beverage", "followers_count": 28400, "district_area": "Panakkukang"},
        {"lead_id": "lead-002", "business_name": "Roti Boy Panakkukang", "platform": "instagram", "handle": "@rotiboy_mks", "category": "fnb_food_resto", "followers_count": 18200, "district_area": "Panakkukang"},
        {"lead_id": "lead-003", "business_name": "Butik Hijab Boulevard", "platform": "instagram", "handle": "@hijabboulevard", "category": "fashion_retail", "followers_count": 34100, "district_area": "Panakkukang"},
        {"lead_id": "lead-004", "business_name": "Kuliner Makassar Viral", "platform": "tiktok", "handle": "@kulinermakassar_viral", "category": "fnb_food_resto", "followers_count": 52000, "district_area": "Rappocini"}
    ]
    for d in defaults:
        h = d["handle"].lstrip("@")
        if h not in seen_handles and len(targets) < 8:
            seen_handles.add(h)
            targets.append(d)

    return targets


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        if parsed.path == "/api/leads/link-channel":
            lead_id = data.get("lead_id")
            platform = data.get("platform", "instagram").lower()
            handle_or_url = data.get("handle_or_url", "").strip()

            target_lead = None
            from_dossier = False
            for lead in get_all_leads():
                if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                    target_lead = adapt_sqlite_lead_for_dashboard(lead) if "channels" not in lead else lead
                    break

            if not target_lead:
                for lead in load_processed_dossiers():
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        from_dossier = True
                        break

            if not target_lead:
                for lead in SAMPLE_LEADS:
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        break

            if not target_lead:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Lead not found"}, ensure_ascii=False).encode("utf-8"))
                return

            if "channels" not in target_lead:
                target_lead["channels"] = {}

            skip_inspection = bool(data.get("skip_inspection", False))
            if platform in ["instagram", "tiktok", "threads"]:
                clean_handle = handle_or_url.replace("https://instagram.com/", "").replace("https://www.instagram.com/", "").replace("https://www.tiktok.com/@", "").replace("https://tiktok.com/@", "").replace("https://threads.net/@", "").replace("https://www.threads.net/@", "").strip("@/")
                clean_handle = clean_handle.split("?")[0].split("#")[0].rstrip("/")
            else:
                clean_handle = handle_or_url.split("?utm_")[0].split("&utm_")[0].strip()
            target_lead["channels"][platform] = clean_handle

            eid = target_lead.get("entity_id") or lead_id
            b_name = target_lead.get("business_name") or ""
            inspection = {"status": "skipped", "posts": target_lead.get("top_posts") or []}

            # 1. Update ke SQLite (digital_footprints) & Dossier secara persisten
            is_sample = str(eid).startswith("lead-")
            persisted = False
            if not is_sample:
                if from_dossier:
                    # Update ke Dossier JSON
                    dossier_saved = persist_channel_to_dossier(eid, platform, clean_handle, inspection.get("posts", []))
                    if dossier_saved:
                        persisted = True
                else:
                    col_map = {
                        "instagram": "instagram_handle",
                        "tiktok": "tiktok_handle",
                        "facebook": "facebook_handle",
                        "threads": "threads_handle",
                        "gofood": "gofood_url",
                        "shopeefood": "shopeefood_url",
                        "grabfood": "grabfood_url",
                        "food_delivery": "food_delivery_url",
                        "fooddelivery": "food_delivery_url"
                    }
                    col = col_map.get(platform)
                    if col:
                        try:
                            from scrapers.db_sqlite import DB_PATH
                            import sqlite3
                            with sqlite3.connect(DB_PATH) as conn:
                                cur = conn.cursor()
                                cur.execute(f"""
                                    INSERT INTO digital_footprints (entity_id, {col})
                                    VALUES (?, ?)
                                    ON CONFLICT(entity_id) DO UPDATE SET {col} = excluded.{col}
                                """, (eid, clean_handle))
                                conn.commit()
                                persisted = True
                        except Exception as sql_err:
                            logger.error(f"Gagal simpan ke SQLite digital_footprints: {sql_err}")

            # 3. Penanganan Antrean Scraping Konten Ponsel Android
            queue_item = None
            if not skip_inspection:
                from scrapers.phone_queue import add_to_queue, update_item_status
                queue_item = add_to_queue(eid, b_name, platform, clean_handle)

                # Jika platform adalah Instagram dan Android terhubung, picu eksekusi background
                if platform == "instagram":
                    dev_status = check_android_device_status()
                    if dev_status.get("connected"):
                        def _run_android_background(q_id, uname, ent_id_target, biz_name):
                            try:
                                update_item_status(q_id, "processing")
                                from scrapers.android_scraper import get_android_device, extract_instagram_profile, persist_profile_to_db, save_raw_output
                                d = get_android_device()
                                profile = extract_instagram_profile(d, uname)
                                if profile.get("status") in ("not_found", "timeout"):
                                    update_item_status(q_id, "failed", f"Status: {profile.get('status')}")
                                else:
                                    save_raw_output(profile, uname)
                                    persist_profile_to_db(profile, entity_id=ent_id_target)
                                    update_item_status(q_id, "completed")
                                    # Kirim info ke Telegram jika ada bridge
                                    try:
                                        from scrapers.telegram_bridge import send_telegram_message, TARGET_CHAT_ID
                                        send_telegram_message(
                                            TARGET_CHAT_ID,
                                            f"[HASIL PERAYAPAN ANDROID]\n"
                                            f"Entitas: {biz_name} ({ent_id_target})\n"
                                            f"Akun: @{uname}\n"
                                            f"Nama: {profile.get('full_name') or uname}\n"
                                            f"WhatsApp: {profile.get('whatsapp_number') or profile.get('contact_phone_number') or '-'}\n"
                                            f"Kategori: {profile.get('business_category') or profile.get('category') or '-'}\n"
                                            f"Followers: {profile.get('followers_count') or 0}"
                                        )
                                    except Exception:
                                        pass
                            except Exception as err:
                                logger.error(f"Error perayapan latar belakang Android: {err}")
                                update_item_status(q_id, "failed", str(err))

                        threading.Thread(
                            target=_run_android_background,
                            args=(queue_item["id"], clean_handle, eid, b_name),
                            daemon=True
                        ).start()

            fresh_lead = find_lead_by_id(eid)
            if fresh_lead:
                target_lead = fresh_lead
            enriched = enrich_lead_card(target_lead)

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"Kanal {platform} berhasil dihubungkan.",
                "persisted": persisted,
                "lead": enriched,
                "inspection": inspection,
                "queue_item": queue_item
            }, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/inspect-content":
            platform = data.get("platform", "instagram")
            handle = data.get("handle") or data.get("target", "")
            business_name = data.get("business_name", "")
            force_refresh = bool(data.get("force_refresh", False))
            dry_run = bool(data.get("dry_run", False))
            result = inspect_account_content(platform, handle, business_name, force_refresh=force_refresh, dry_run=dry_run)

            lead_id = data.get("lead_id")
            if lead_id and result.get("status") == "success" and result.get("posts"):
                target_lead = find_lead_by_id(lead_id)
                if target_lead:
                    target_lead["top_posts"] = result["posts"]
                    if "channels" not in target_lead:
                        target_lead["channels"] = {}
                    target_lead["channels"][platform.lower()] = clean_social_handle(handle)
                    target_lead["latest_post_date"] = (datetime.now() - timedelta(days=1)).isoformat()
                    target_lead["is_active_verified"] = True
                    save_inspected_posts_to_sqlite(target_lead.get("entity_id") or lead_id, platform, result["posts"])
                    enrich_lead_card(target_lead)

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/inspector/link-lead":
            lead_id = data.get("lead_id")
            platform = data.get("platform", "instagram").lower()
            handle = data.get("handle", "")
            posts = data.get("posts", [])

            if not lead_id:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "lead_id wajib diisi"}, ensure_ascii=False).encode("utf-8"))
                return

            target_lead = find_lead_by_id(lead_id)
            if not target_lead:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Lead not found"}, ensure_ascii=False).encode("utf-8"))
                return

            if "channels" not in target_lead:
                target_lead["channels"] = {}
            if handle:
                target_lead["channels"][platform] = clean_social_handle(handle)

            if posts:
                target_lead["top_posts"] = posts
                target_lead["latest_post_date"] = (datetime.now() - timedelta(days=1)).isoformat()
                target_lead["is_active_verified"] = True

            entity_id = target_lead.get("entity_id") or lead_id
            saved_count = save_inspected_posts_to_sqlite(entity_id, platform, posts)
            persist_channel_to_dossier(entity_id, platform, clean_social_handle(handle), posts)

            enriched = enrich_lead_card(target_lead)

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"Hasil inspeksi berhasil ditautkan ke calon customer {target_lead.get('business_name', '')}.",
                "saved_posts_count": saved_count,
                "lead": enriched
            }, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/leads/update-status":
            lead_id = data.get("lead_id")
            status = data.get("status") or data.get("outreach_status")
            notes = data.get("notes") if data.get("notes") is not None else data.get("outreach_notes", "")
            reason = data.get("reason", "")
            if reason and not notes:
                notes = f"Alasan: {reason}"

            if not lead_id or not status:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "lead_id dan status wajib diisi"}, ensure_ascii=False).encode("utf-8"))
                return

            if status not in VALID_OUTREACH_STATUSES:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Status tidak valid. Pilihan valid: {', '.join(VALID_OUTREACH_STATUSES)}"
                }, ensure_ascii=False).encode("utf-8"))
                return
            target_lead = None
            from_dossier = False
            for lead in get_all_leads():
                if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                    target_lead = adapt_sqlite_lead_for_dashboard(lead) if "channels" not in lead else lead
                    break

            if not target_lead:
                for lead in load_processed_dossiers():
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        from_dossier = True
                        break

            if not target_lead:
                for lead in SAMPLE_LEADS:
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        break

            if not target_lead:
                # Coba update langsung ke tabel leads SQLite jika ada
                if update_lead_status_in_db(lead_id, status, reason or notes):
                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "message": f"Lead {lead_id} status updated to {status}",
                        "persisted": True
                    }, ensure_ascii=False).encode("utf-8"))
                    return

                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Lead not found"}, ensure_ascii=False).encode("utf-8"))
                return

            target_lead["outreach_status"] = status
            target_lead["outreach_notes"] = notes
            target_lead["sales_notes"] = notes
            if status in ("Dihubungi", "Closing"):
                target_lead["contacted_at"] = datetime.now().isoformat()

            persisted = False
            entity_id_target = target_lead.get("entity_id") or lead_id
            is_sample = str(entity_id_target).startswith("lead-")
            if not is_sample:
                if from_dossier:
                    persist_status_to_dossier(entity_id_target, status, notes)
                    persisted = True
                else:
                    try:
                        update_outreach_log(entity_id_target, status, notes)
                        persisted = True
                    except Exception:
                        pass

                    try:
                        if update_lead_status_in_db(lead_id, status, reason or notes):
                            persisted = True
                    except Exception:
                        pass
            else:
                persisted = True

            enriched = enrich_lead_card(target_lead)

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "message": "Status penjangkauan berhasil diperbarui.",
                "persisted": persisted,
                "lead": enriched
            }, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/leads/override-score":
            lead_id = data.get("lead_id")
            manual_tier = (data.get("manual_tier") or "").strip()
            manual_score = data.get("manual_score")
            manual_notes = (data.get("manual_notes") or "").strip()

            if not lead_id:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "lead_id wajib diisi"}, ensure_ascii=False).encode("utf-8"))
                return

            if manual_tier and manual_tier not in VALID_OVERRIDE_TIERS:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Tier tidak valid. Pilihan valid: {', '.join(VALID_OVERRIDE_TIERS)}"
                }, ensure_ascii=False).encode("utf-8"))
                return

            if manual_score is not None:
                try:
                    manual_score = int(manual_score)
                except (TypeError, ValueError):
                    self.send_response(400)
                    self.send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "manual_score harus berupa angka"}, ensure_ascii=False).encode("utf-8"))
                    return
                if not (0 <= manual_score <= 100):
                    self.send_response(400)
                    self.send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "manual_score harus 0 - 100"}, ensure_ascii=False).encode("utf-8"))
                    return

            is_override = bool(manual_tier) or manual_score is not None
            if not is_override:
                manual_tier, manual_score, manual_notes = "", None, ""

            target_lead = None
            from_dossier = False
            for lead in get_all_leads():
                if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                    target_lead = adapt_sqlite_lead_for_dashboard(lead) if "channels" not in lead else lead
                    break

            if not target_lead:
                for lead in load_processed_dossiers():
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        from_dossier = True
                        break

            if not target_lead:
                for lead in SAMPLE_LEADS:
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        break

            if not target_lead:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Lead not found"}, ensure_ascii=False).encode("utf-8"))
                return

            target_lead["manual_tier"] = manual_tier
            target_lead["manual_score"] = manual_score
            target_lead["manual_notes"] = manual_notes
            target_lead["is_manual_override"] = is_override

            persisted = False
            entity_id_target = target_lead.get("entity_id") or lead_id
            is_sample = str(entity_id_target).startswith("lead-")
            try:
                persisted = update_manual_override(entity_id_target, manual_tier, manual_score, manual_notes, is_override)
            except Exception:
                pass
            if from_dossier:
                persisted = persist_manual_override_to_dossier(entity_id_target, manual_tier, manual_score, manual_notes, is_override) or persisted
            if is_sample:
                persisted = True

            enriched = enrich_lead_card(target_lead)

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "message": "Penyesuaian manual berhasil disimpan.",
                "persisted": persisted,
                "lead": enriched
            }, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/sync-hermes":
            try:
                sheet_name = data.get("sheet_name", "Radar Prospek")
                clear_first = bool(data.get("clear_first", False))
                dry_run = bool(data.get("dry_run", False))

                if sheet_name == "Matriks Kompetitor":
                    from scrapers.competitor_matrix import sync_competitor_matrix_to_hermes
                    res = sync_competitor_matrix_to_hermes(
                        sheet_name=sheet_name,
                        clear_first=clear_first,
                        dry_run=dry_run
                    )
                else:
                    from scrapers.sync_hermes import sync_leads_to_hermes
                    all_leads = get_all_leads()
                    res = sync_leads_to_hermes(
                        leads=all_leads,
                        sheet_name=sheet_name,
                        clear_first=clear_first,
                        dry_run=dry_run
                    )
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            except Exception as exc:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/android/scrape":
            username = data.get("username", "")
            dry_run = data.get("dry_run", False)
            
            if not username:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "username is required"
                }, ensure_ascii=False).encode("utf-8"))
                return
            
            try:
                from scrapers.android_scraper import get_android_device, extract_instagram_profile
                
                device = get_android_device()
                profile = extract_instagram_profile(device, username)
                
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "profile": profile
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as exc:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": str(exc)
                }, ensure_ascii=False).encode("utf-8"))
        if parsed.path in ("/api/android/run-queue", "/api/queue/run"):
            from scrapers.phone_queue import get_pending_items, update_item_status
            pending = get_pending_items()
            if not pending:
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "empty",
                    "message": "Tidak ada akun dalam antrean pending."
                }, ensure_ascii=False).encode("utf-8"))
                return

            dev_status = check_android_device_status()
            if not dev_status.get("connected"):
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "Perangkat Android tidak terhubung via USB."
                }, ensure_ascii=False).encode("utf-8"))
                return

            def _batch_queue_worker(items):
                from scrapers.android_scraper import get_android_device, extract_instagram_profile, persist_profile_to_db, save_raw_output
                d = get_android_device()
                for it in items:
                    q_id = it["id"]
                    uname = it["handle"]
                    update_item_status(q_id, "processing")
                    try:
                        profile = extract_instagram_profile(d, uname)
                        if profile.get("status") in ("not_found", "timeout"):
                            update_item_status(q_id, "failed", profile.get("status"))
                        else:
                            save_raw_output(profile, uname)
                            persist_profile_to_db(profile, entity_id=it.get("lead_id"))
                            update_item_status(q_id, "completed")
                    except Exception as exc:
                        update_item_status(q_id, "failed", str(exc))

            threading.Thread(target=_batch_queue_worker, args=(pending,), daemon=True).start()

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "started",
                "message": f"Memulai perayapan untuk {len(pending)} akun pada perangkat Android.",
                "total": len(pending)
            }, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # API Endpoint: Get Android Scraping Queue
        if parsed.path in ("/api/android/queue", "/api/queue"):
            from scrapers.phone_queue import load_queue
            q_data = load_queue()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(q_data, ensure_ascii=False).encode("utf-8"))
            return

        # API Endpoint: Status Perangkat Android
        if parsed.path == "/api/device/status":
            status = check_android_device_status()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status, ensure_ascii=False).encode("utf-8"))
            return

        # API Endpoint: Get Leads
        if parsed.path == "/api/leads":
            leads = get_all_leads()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(leads, ensure_ascii=False).encode("utf-8"))
            return

        # API Endpoint: Get Single Lead
        if parsed.path == "/api/lead":
            params = urllib.parse.parse_qs(parsed.query)
            lead_id = params.get("id", [None])[0]
            leads = get_all_leads()
            found = next((l for l in leads if l.get("id") == lead_id or l.get("entity_id") == lead_id), None)
            if found:
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(found, ensure_ascii=False).encode("utf-8"))
            else:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Lead not found"}, ensure_ascii=False).encode("utf-8"))
            return

        # API Endpoint: Inspector Quick Targets
        if parsed.path == "/api/inspector/quick-targets":
            targets = get_inspector_quick_targets()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(targets, ensure_ascii=False).encode("utf-8"))
            return
            
        # Serve Frontend HTML
        if parsed.path in ["/", "/market-scraping", "/market-scraping/"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_file = PROJECT_ROOT / "docs" / "dashboard" / "index.html"
            if html_file.exists():
                with open(html_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"<h1>Dashboard File Not Found</h1>")
            return
            
        # Serve Static Assets dari docs/dashboard/
        path_clean = parsed.path.lstrip("/")
        if path_clean.startswith("market-scraping/"):
            path_clean = path_clean[len("market-scraping/"):]
        static_file = PROJECT_ROOT / "docs" / "dashboard" / path_clean
        if static_file.exists() and static_file.is_file():
            self.send_response(200)
            if static_file.suffix == ".css":
                self.send_header("Content-Type", "text/css; charset=utf-8")
            elif static_file.suffix == ".js":
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
            elif static_file.suffix == ".png":
                self.send_header("Content-Type", "image/png")
            elif static_file.suffix == ".svg":
                self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
            with open(static_file, "rb") as f:
                self.wfile.write(f.read())
            return
            
        self.send_response(404)
        self.end_headers()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_server():
    ThreadedTCPServer.allow_reuse_address = True
    with ThreadedTCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"RUANG VISUAL Market Intelligence Dashboard aktif di: http://localhost:{PORT}/market-scraping")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server dihentikan.")


if __name__ == "__main__":
    start_server()
