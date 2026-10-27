import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import http.server
import socketserver
import urllib.parse
from typing import Optional
from datetime import datetime, timedelta
from scrapers.lead_scoring import (
    classify_category,
    calculate_score,
    calculate_4_pillars_score,
    infer_product_needs,
    generate_whatsapp_pitch,
    estimate_packaging_volume_and_value,
)
from scrapers.db_sqlite import get_all_leads as get_all_leads_from_sqlite, update_outreach_log
from scrapers.exporter import export_dossiers_to_csv, export_full_dossiers_to_csv, find_latest_dossier
from scrapers.content_inspector import (
    fetch_social_top_posts,
    save_inspected_posts_to_sqlite,
    clean_social_handle
)

PORT = 3000

from scrapers.sample_leads import SAMPLE_LEADS


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
            "threads": "",
            "food_delivery": ""
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
        })
    return leads


VALID_OUTREACH_STATUSES = (
    "Belum Dihubungi",
    "Dihubungi",
    "Tertarik",
    "Closing",
    "Tidak Relevan",
)


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

    channels = {
        "google_maps": f"https://maps.google.com/?cid={place_id}" if place_id else "",
        "instagram": ig,
        "tiktok": tt,
        "threads": "",
        "food_delivery": "",
    }

    status = item.get("outreach_status") or "Belum Dihubungi"
    notes = item.get("sales_notes") or ""

    return {
        "id": entity_id,
        "entity_id": entity_id,
        "business_name": item.get("business_name") or "",
        "category": cat,
        "target_sector": item.get("target_sector") or "",
        "primary_service_pillar": item.get("primary_service_pillar") or "",
        "platforms": ["google_maps"] + (["instagram"] if ig else []) + (["tiktok"] if tt else []),
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
        "top_posts": [],
        "whatsapp_pitch": item.get("whatsapp_pitch") or "",
        "is_active_verified": bool(item.get("is_wa_valid") or wa),
        "is_ad_active": bool(item.get("has_meta_ads")),
        "has_meta_ads": bool(item.get("has_meta_ads")),
        "status": "ready_to_pitch" if wa else "new_lead",
        "outreach_status": status,
        "outreach_notes": notes,
        "sales_notes": notes,
        "contacted_at": item.get("contacted_at"),
    }


def get_all_leads():
    # 1. SQLite (Utama)
    leads_sqlite = get_all_leads_from_sqlite()
    if leads_sqlite:
        return [enrich_lead_card(adapt_sqlite_lead_for_dashboard(item)) for item in leads_sqlite]

    # 2. Fallback (Dossier & Raw)
    processed = load_processed_dossiers()
    scraped = load_raw_scraped_leads()
    seen = {p["business_name"].lower() for p in processed if p.get("business_name")}
    combined = list(processed)
    combined += [s for s in scraped if s["business_name"].lower() not in seen]
    
    seen = {c["business_name"].lower() for c in combined if c.get("business_name")}
    for sample in SAMPLE_LEADS:
        if sample.get("business_name", "").lower() not in seen:
            combined.append(sample)

    return [enrich_lead_card(item) for item in combined]


def find_lead_by_id(lead_id: str) -> Optional[dict]:
    if not lead_id:
        return None
    for lead in SAMPLE_LEADS:
        if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
            return lead
    for lead in load_processed_dossiers():
        if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
            return lead
    for lead in get_all_leads():
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
            for lead in SAMPLE_LEADS:
                if lead["id"] == lead_id:
                    target_lead = lead
                    break

            from_dossier = False
            if not target_lead:
                for lead in load_processed_dossiers():
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        from_dossier = True
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

            clean_handle = handle_or_url.replace("https://instagram.com/", "").replace("https://www.tiktok.com/@", "").strip("@/")
            target_lead["channels"][platform] = clean_handle
            
            inspection = inspect_account_content(platform, clean_handle, target_lead.get("business_name", ""))
            target_lead["top_posts"] = inspection["posts"]
            if inspection["posts"]:
                target_lead["latest_post_date"] = (datetime.now() - timedelta(days=1)).isoformat()
                target_lead["is_active_verified"] = True

            persisted = False
            if from_dossier:
                persisted = persist_channel_to_dossier(
                    target_lead.get("entity_id") or lead_id, platform, clean_handle, inspection["posts"])

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
                "inspection": inspection
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
            for lead in SAMPLE_LEADS:
                if lead["id"] == lead_id:
                    target_lead = lead
                    break

            from_dossier = False
            if not target_lead:
                for lead in load_processed_dossiers():
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        from_dossier = True
                        break

            if not target_lead:
                for lead in get_all_leads():
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

            target_lead["outreach_status"] = status
            target_lead["outreach_notes"] = notes
            target_lead["sales_notes"] = notes
            if status in ("Dihubungi", "Closing"):
                target_lead["contacted_at"] = datetime.now().isoformat()

            persisted = False
            entity_id_target = target_lead.get("entity_id") or lead_id
            try:
                update_outreach_log(entity_id_target, status, notes)
                persisted = True
            except Exception:
                pass

            if from_dossier:
                persist_status_to_dossier(entity_id_target, status, notes)

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

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # API Endpoint: Unduh CSV dossier terpadu
        if parsed.path == "/api/export/csv":
            try:
                json_path = find_latest_dossier()
                if not json_path or not json_path.exists():
                    raise FileNotFoundError("Tidak ada berkas dossier terpadu yang ditemukan.")
                import json as _json
                dossiers = _json.loads(json_path.read_text(encoding='utf-8'))
                csv_path = PROJECT_ROOT / "data" / "processed" / "dossiers_export_ruang_visual.csv"
                export_dossiers_to_csv(dossiers, csv_path)
            except (FileNotFoundError, ValueError, OSError) as exc:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))
                return
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="dossiers_export_ruang_visual.csv"')
            self.end_headers()
            self.wfile.write(csv_path.read_bytes())
            return

        # API Endpoint: Unduh CSV 32 Kolom (Full)
        if parsed.path == "/api/export/csv-full":
            try:
                all_leads = get_all_leads()
                csv_path = PROJECT_ROOT / "data" / "processed" / "dossiers_export_full.csv"
                export_full_dossiers_to_csv(all_leads, csv_path)
            except Exception as exc:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))
                return
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="dossiers_export_full.csv"')
            self.end_headers()
            self.wfile.write(csv_path.read_bytes())
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


def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    try:
        from scrapers.db_sqlite import seed_sample_leads_to_sqlite
        seeded = seed_sample_leads_to_sqlite()
        if seeded > 0:
            print(f"Database SQLite lokal terverifikasi ({seeded} prospek tersinkron).")
    except Exception as e:
        print(f"Peringatan: Gagal seeding database SQLite: {e}")

    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"RUANG VISUAL Market Intelligence Dashboard aktif di: http://localhost:{PORT}/market-scraping")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server dihentikan.")


if __name__ == "__main__":
    start_server()
