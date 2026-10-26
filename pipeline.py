import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
from datetime import datetime
from scrapers.gmaps_scraper import search_places, scrape_negative_reviews
from scrapers.instagram_scraper import run_follower_spider, enrich_profile, validate_recency
from scrapers.meta_ads_scraper import search_meta_ads
from scrapers.tiktok_scraper import scrape_tiktok_search, transform_to_lead_format as transform_tiktok_leads
from scrapers.threads_scraper import scrape_threads_profile
from scrapers.food_delivery_scraper import scrape_gofood, scrape_grabfood, scrape_shopeefood
from scrapers.normalizer import normalize_whatsapp, normalize_address
from scrapers.lead_scoring import qualify_lead, calculate_score, classify_category, infer_product_needs, generate_whatsapp_pitch, calculate_4_pillars_score
from scrapers.entity_matcher import load_raw_records, match_entities
from scrapers.outreach_generator import generate_whatsapp_pitch as generate_outreach_pitch, _resolve_sector
from scrapers.route_cluster import assign_sales_cluster
from scrapers.exporter import export_dossiers_to_csv, find_latest_dossier
from scrapers.database import insert_lead, get_supabase_client, batch_upsert_dossiers
from scrapers.harvest_makassar import harvest
from scrapers.sync_catalog import sync_catalog
from scrapers.db_sqlite import init_db, upsert_lead as upsert_lead_sqlite
from scrapers.normalizer import validate_whatsapp_number
import os
from pathlib import Path
from datetime import datetime, timedelta


def ensure_catalog_synced(max_age_days: int = 7):
    catalog_path = Path("data/catalog/ruang_visual_catalog.json")
    
    if not catalog_path.exists():
        print("Katalog tidak ditemukan. Melakukan sinkronisasi...")
        sync_catalog()
        return
    
    file_age = datetime.now() - datetime.fromtimestamp(catalog_path.stat().st_mtime)
    if file_age.days > max_age_days:
        print(f"Katalog sudah berusia {file_age.days} hari (lebih dari {max_age_days} hari). Melakukan sinkronisasi ulang...")
        sync_catalog()
    else:
        print(f"Katalog masih segar (usia {file_age.days} hari).")


def run_gmaps_pipeline(query: str, city: str, limit: int, dry_run: bool, save_db: bool):
    print(f"Menjalankan pipeline Google Maps: '{query}' di {city} (Limit: {limit}, Dry-run: {dry_run})")
    places = search_places(query=query, city=city, limit=limit, dry_run=dry_run)
    
    if dry_run or not places:
        print("Pipeline selesai (mode dry-run aktif atau tidak ada hasil).")
        return
    
    qualified_count = 0
    saved_count = 0
    
    for item in places:
        lead = {
            "business_name": item.get("title", ""),
            "platform": "google_maps",
            "google_maps_place_id": item.get("place_id"),
            "whatsapp_number": item.get("whatsapp_number"),
            "phone_office": item.get("phone_number"),
            "address_full": item.get("address"),
            "district_area": item.get("district_area"),
            "city": item.get("city") or city,
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "external_website_url": item.get("website")
        }
        
        category = classify_category(lead["business_name"], item.get("category_name", ""), [])
        lead["category"] = category
        
        is_qualified, reason = qualify_lead(lead)
        if not is_qualified:
            print(f"Prospek gugur: {lead['business_name']} - Alasan: {reason}")
            continue
        
        qualified_count += 1
        score = calculate_score(lead)
        needs = infer_product_needs(category, lead["business_name"], "")
        pitch_info = generate_whatsapp_pitch(lead)
        products_str = ", ".join(needs["recommended_products"][:3])
        print(f"Prospek lolos: {lead['business_name']} | Kategori: {category} | Skor: {score}")
        print(f"  Rekomendasi Cetak: {products_str}")
        if pitch_info:
            print(f"  Draft Pitch WA: {pitch_info['wa_link']}")
        
        if save_db:
            ok, msg = insert_lead(lead, score=score, dry_run=dry_run)
            if ok:
                saved_count += 1
                print(f"Tersimpan ke database: {lead['business_name']}")
            else:
                print(f"Gagal simpan database: {msg}")
    
    print(f"Selesai. Total ditemukan: {len(places)}, Lolos kualifikasi: {qualified_count}, Tersimpan: {saved_count}")


def run_instagram_pipeline(target: str, limit: int, dry_run: bool, save_db: bool):
    print(f"Menjalankan pipeline Instagram untuk target @{target} (Limit: {limit}, Dry-run: {dry_run})")
    
    profile = enrich_profile(target, dry_run=dry_run)
    if dry_run or not profile:
        print("Pipeline selesai (mode dry-run aktif atau tidak ada data profil).")
        return
    
    is_active = validate_recency(profile)
    timestamps = profile.get("latest_post_timestamps", [])
    last_post = timestamps[0] if timestamps else None
    
    lead = {
        "business_name": profile.get("username", target),
        "platform": "instagram",
        "platform_handle": target,
        "platform_profile_url": f"https://instagram.com/{target}",
        "whatsapp_number": profile.get("whatsapp_number"),
        "follower_count": profile.get("followers_count", 0),
        "external_website_url": profile.get("external_url"),
        "biography": profile.get("biography", ""),
        "latest_post_date": last_post,
        "is_active_verified": is_active
    }
    
    lead["category"] = classify_category(lead["business_name"], lead["biography"], [])
    
    is_qualified, reason = qualify_lead(lead)
    if not is_qualified:
        print(f"Prospek gugur: @{target} - Alasan: {reason}")
        return
    
    score = calculate_score(lead)
    print(f"Prospek lolos: @{target} | Skor: {score} | Aktif: {is_active}")
    
    if save_db:
        ok, msg = insert_lead(lead, score=score, dry_run=dry_run)
        if ok:
            print(f"Tersimpan ke database: @{target}")
        else:
            print(f"Gagal simpan database: {msg}")


def run_meta_ads_pipeline(query: str, limit: int, dry_run: bool, save_db: bool):
    print(f"Menjalankan pipeline Meta Ads: '{query}' (Limit: {limit}, Dry-run: {dry_run})")
    ads = search_meta_ads(query=query, limit=limit, dry_run=dry_run)
    
    if dry_run or not ads:
        print("Pipeline selesai (mode dry-run aktif atau tidak ada hasil iklan).")
        return
    
    qualified_count = 0
    saved_count = 0
    
    for ad in ads:
        external_links = ad.get("external_links", [])
        primary_link = external_links[0] if external_links else ""
        
        lead = {
            "business_name": ad.get("page_name", ""),
            "platform": "facebook_ads",
            "platform_id": ad.get("page_id"),
            "whatsapp_number": ad.get("whatsapp_number"),
            "is_ad_active": True,
            "external_website_url": primary_link,
            "is_active_verified": True
        }
        
        category = classify_category(lead["business_name"], ad.get("ad_creative_body", ""), [])
        lead["category"] = category
        
        is_qualified, reason = qualify_lead(lead)
        if not is_qualified:
            print(f"Prospek gugur: {lead['business_name']} - Alasan: {reason}")
            continue
        
        qualified_count += 1
        score = calculate_score(lead)
        print(f"Prospek lolos: {lead['business_name']} | Kategori: {category} | Skor: {score}")
        
        if save_db:
            ok, msg = insert_lead(lead, score=score, dry_run=dry_run)
            if ok:
                saved_count += 1
                print(f"Tersimpan ke database: {lead['business_name']}")
            else:
                print(f"Gagal simpan database: {msg}")
    
    print(f"Selesai. Total ditemukan: {len(ads)}, Lolos kualifikasi: {qualified_count}, Tersimpan: {saved_count}")


def run_tiktok_pipeline(keyword: str, limit: int, dry_run: bool, save_db: bool):
    print(f"Menjalankan pipeline TikTok untuk '{keyword}' (Limit: {limit}, Dry-run: {dry_run})")
    raw_results = scrape_tiktok_search(keyword=keyword, limit=limit, dry_run=dry_run)
    if dry_run or not raw_results:
        print("Pipeline selesai (mode dry-run aktif atau tidak ada hasil).")
        return
    
    leads = transform_tiktok_leads(raw_results)
    qualified_count = 0
    saved_count = 0
    
    for item in leads:
        lead = {
            "business_name": item.get("display_name") or item.get("username", ""),
            "platform": "tiktok",
            "platform_handle": item.get("username", ""),
            "platform_profile_url": f"https://www.tiktok.com/{item.get('username', '')}",
            "whatsapp_number": item.get("whatsapp_number"),
            "external_website_url": item.get("bio_link"),
            "biography": item.get("bio_text", ""),
            "last_post_date": item.get("last_post_date"),
            "is_active_verified": item.get("is_active", True)
        }
        
        category = classify_category(lead["business_name"], lead["biography"], item.get("relevant_hashtags", []))
        lead["category"] = category
        
        is_qualified, reason = qualify_lead(lead)
        if not is_qualified:
            print(f"Prospek gugur: {lead['business_name']} - Alasan: {reason}")
            continue
        
        qualified_count += 1
        score = calculate_score(lead)
        print(f"Prospek lolos: {lead['business_name']} | Kategori: {category} | Skor: {score}")
        
        if save_db:
            ok, msg = insert_lead(lead, score=score, dry_run=dry_run)
            if ok:
                saved_count += 1
                print(f"Tersimpan ke database: {lead['business_name']}")
            else:
                print(f"Gagal simpan database: {msg}")
    
    print(f"Selesai. Total ditemukan: {len(leads)}, Lolos kualifikasi: {qualified_count}, Tersimpan: {saved_count}")


def run_threads_pipeline(username: str, limit: int, dry_run: bool, save_db: bool):
    print(f"Menjalankan pipeline Threads untuk @{username} (Limit: {limit}, Dry-run: {dry_run})")
    profile = scrape_threads_profile(username=username, limit=limit, dry_run=dry_run)
    if dry_run or not profile:
        print("Pipeline selesai (mode dry-run aktif atau tidak ada hasil).")
        return

    lead = {
        "business_name": profile.get("business_name", ""),
        "platform": "threads",
        "platform_handle": username,
        "platform_profile_url": f"https://threads.net/@{username}",
        "whatsapp_number": profile.get("whatsapp_number"),
        "biography": profile.get("biography", ""),
        "last_post_date": profile.get("last_post_date"),
        "is_active_verified": profile.get("is_active", False)
    }

    category = classify_category(lead["business_name"], lead["biography"], [])
    lead["category"] = category

    is_qualified, reason = qualify_lead(lead)
    if not is_qualified:
        print(f"Prospek gugur: @{username} - Alasan: {reason}")
        return

    score = calculate_score(lead)
    print(f"Prospek lolos: @{username} | Skor: {score} | Aktif: {lead['is_active_verified']}")

    if save_db:
        ok, msg = insert_lead(lead, score=score, dry_run=dry_run)
        if ok:
            print(f"Tersimpan ke database: @{username}")
        else:
            print(f"Gagal simpan database: {msg}")


def run_food_delivery_pipeline(platform: str, city: str, limit: int, dry_run: bool, save_db: bool):
    print(f"Menjalankan pipeline {platform.upper()} di {city} (Limit: {limit}, Dry-run: {dry_run})")
    
    if platform == "gofood":
        merchants = scrape_gofood(city=city, limit=limit, dry_run=dry_run)
    elif platform == "grabfood":
        merchants = scrape_grabfood(city=city, limit=limit, dry_run=dry_run)
    elif platform == "shopeefood":
        merchants = scrape_shopeefood(city=city, limit=limit, dry_run=dry_run)
    else:
        print(f"Platform tidak dikenal: {platform}")
        return

    if dry_run or not merchants:
        print("Pipeline selesai (mode dry-run aktif atau tidak ada hasil).")
        return

    qualified_count = 0
    saved_count = 0

    for item in merchants:
        lead = {
            "business_name": item.get("merchant_name", ""),
            "platform": item.get("platform", platform),
            "platform_id": item.get("merchant_id"),
            "whatsapp_number": item.get("phone_number"),
            "address_full": item.get("address_full"),
            "district_area": item.get("district_area"),
            "city": item.get("city") or city,
            "category": item.get("classified_category") or classify_category(item.get("merchant_name", ""), item.get("category", ""), []),
            "is_active_verified": True,
            "packaging_pain_points": item.get("packaging_pain_points", []),
            "estimated_commercials": item.get("estimated_commercials", {})
        }

        is_qualified, reason = qualify_lead(lead)
        if not is_qualified:
            print(f"Prospek gugur: {lead['business_name']} - Alasan: {reason}")
            continue

        qualified_count += 1
        score = calculate_score(lead)
        print(f"Prospek lolos: {lead['business_name']} | Skor: {score}")

        if save_db:
            ok, msg = insert_lead(lead, score=score, dry_run=dry_run)
            if ok:
                saved_count += 1
                print(f"Tersimpan ke database: {lead['business_name']}")
            else:
                print(f"Gagal simpan database: {msg}")

    print(f"Selesai. Total ditemukan: {len(merchants)}, Lolos kualifikasi: {qualified_count}, Tersimpan: {saved_count}")


_SECTOR_PILLAR = {
    'education': 'office_school',
    'corporate_legal': 'office_school',
    'event_community': 'custom_merch',
    'retail_apparel': 'apparel',
    'fnb_hospitality': 'label_sticker',
    'beauty_skincare': 'label_sticker',
    'general': 'advertising',
}


def sync_entities_to_sqlite(entities: list, city: str, db_path=None) -> int:
    init_db(db_path)
    saved = 0
    for ent in entities:
        sector = _resolve_sector(ent.get('category', ''), ent)
        wa_raw = ent.get('whatsapp_number') or ent.get('phone_number') or ''
        is_wa_valid, wa_normalized = validate_whatsapp_number(wa_raw)
        pillars = calculate_4_pillars_score(ent)
        address = ent.get('address_full', '')
        district = ent.get('district_area', '')
        entity_data = {
            'entity_id': ent.get('entity_id', ''),
            'business_name': ent.get('business_name', ''),
            'target_sector': sector,
            'primary_service_pillar': _SECTOR_PILLAR.get(sector, 'advertising'),
            'category_raw': ent.get('category', ''),
            'whatsapp_number': wa_normalized or wa_raw or None,
            'phone_raw': ent.get('phone_number'),
            'is_wa_valid': 1 if is_wa_valid else 0,
            'is_commercial': 1,
            'locations': {
                'place_id': ent.get('google_maps_place_id') or ent.get('place_id'),
                'address_full': address,
                'district_area': district,
                'city': city,
                'sales_cluster': assign_sales_cluster(address, district),
                'latitude': ent.get('latitude'),
                'longitude': ent.get('longitude'),
            },
            'digital_footprints': {
                'website_url': ent.get('external_website_url'),
                'gmaps_rating': ent.get('rating'),
                'gmaps_reviews_count': ent.get('reviews_count', 0),
                'review_snippets_json': ent.get('review_snippets') or [],
                'instagram_handle': ent.get('instagram_handle'),
                'instagram_bio': ent.get('biography'),
                'instagram_followers': ent.get('followers_count', 0),
                'latest_post_date': ent.get('last_post_date'),
                'tiktok_handle': ent.get('tiktok_handle'),
                'has_meta_ads': 1 if ent.get('is_ad_active') else 0,
            },
            'commercial_intelligence': {
                'lead_score': pillars.get('score_total', 0),
                'priority_tier': ent.get('priority_tier') or pillars.get('tier', 'Tier D'),
                'score_legitimacy': pillars.get('score_legitimacy', 0),
                'score_velocity': pillars.get('score_velocity', 0),
                'score_turnover': pillars.get('score_turnover', 0),
                'score_budget': pillars.get('score_budget', 0),
                'detected_service_needs': ent.get('detected_service_needs') or [],
                'service_pain_points': ent.get('packaging_pain_points') or [],
                'est_order_value_idr': (ent.get('estimated_commercials') or {}).get('est_monthly_value_min_idr', 0),
                'recommended_products': ent.get('recommended_products', ''),
            },
            'outreach_logs': {
                'outreach_status': 'Belum Dihubungi',
                'whatsapp_pitch': ent.get('whatsapp_pitch', ''),
            },
        }
        try:
            if upsert_lead_sqlite(entity_data, db_path):
                saved += 1
        except Exception as e:
            print(f"Gagal menyimpan entitas {ent.get('entity_id')} ke SQLite: {e}")
    return saved


def run_match_pipeline(raw_dir: str, output_dir: str, city: str, dry_run: bool, save_db: bool = False):
    print(f"Menjalankan entity matcher lintas platform (Raw: {raw_dir}, Kota: {city}, Dry-run: {dry_run})")
    
    ensure_catalog_synced()

    records = load_raw_records(Path(raw_dir), limit=10000)
    print(f"Record mentah dibaca: {len(records)}")
    if not records:
        print("Tidak ada data mentah untuk dicocokkan. Pipeline selesai.")
        return

    entities = match_entities(records)
    merge_keys = ('whatsapp_number', 'phone_number', 'address_full', 'latitude', 'longitude',
                  'last_post_date', 'followers_count', 'reviews_count', 'is_ad_active',
                  'is_active_verified', 'external_website_url', 'category', 'packaging_pain_points', 'sector')
    for ent in entities:
        for key in merge_keys:
            if ent.get(key):
                continue
            for rec in ent['records']:
                if isinstance(rec, dict) and rec.get(key):
                    ent[key] = rec[key]
                    break
        if not ent.get('last_post_date'):
            for rec in ent['records']:
                if isinstance(rec, dict) and (rec.get('latest_post_date') or rec.get('last_post_date')):
                    ent['last_post_date'] = rec.get('latest_post_date') or rec.get('last_post_date')
                    break
        if not ent.get('rating'):
            for rec in ent['records']:
                if isinstance(rec, dict) and (rec.get('total_score') or rec.get('rating')):
                    ent['rating'] = rec.get('total_score') or rec.get('rating')
                    break
        if not ent.get('category') or ent.get('category') == 'general_commercial':
            bio = ent.get('biography') or ''
            raw_cat = ''
            for rec in ent['records']:
                if isinstance(rec, dict):
                    raw_cat = raw_cat or rec.get('category_name') or rec.get('category_raw') or ''
            reclassified = classify_category(ent.get('business_name', ''), f"{bio} {raw_cat}", [])
            if reclassified != 'general_commercial' or not ent.get('category'):
                ent['category'] = reclassified
        score = calculate_score(ent)
        ent['lead_score'] = score
        ent['priority_tier'] = 'Tier A' if score >= 80 else 'Tier B' if score >= 60 else 'Tier C' if score >= 40 else 'Tier D'
        ent['whatsapp_pitch'] = generate_outreach_pitch(ent)
        from scrapers.outreach_generator import recommended_products as get_rec_products
        ent['recommended_products'] = get_rec_products(ent)
    merged_count = sum(1 for e in entities if len(e['records']) > 1)
    print(f"Entitas unik: {len(entities)} | Entitas gabungan lintas platform: {merged_count}")

    for ent in entities:
        if len(ent['records']) > 1:
            print(f"  {ent['entity_id']}: {ent['business_name']} | Platform: {', '.join(ent['platforms'])} "
                  f"| WhatsApp: {ent['whatsapp_number'] or '-'} | Alasan: {', '.join(ent['match_reasons'])}")

    out_name = f"unified_dossiers_{city}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if dry_run:
        print(f"Mode dry-run aktif: berkas {out_name} tidak ditulis.")
        return

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    out_path = out_path / out_name
    out_path.write_text(json.dumps(entities, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Dossier terpadu disimpan: {out_path}")

    if save_db:
        count, msg = batch_upsert_dossiers(entities, dry_run=False)
        print(msg)

    saved_sqlite = sync_entities_to_sqlite(entities, city)
    print(f"Entitas tersimpan ke SQLite (data/leads.sqlite): {saved_sqlite}")


def run_export_pipeline(input_path: str, output_path: str, dry_run: bool, include_no_wa: bool = False):
    json_path = Path(input_path) if input_path else find_latest_dossier(PROJECT_ROOT / 'data' / 'processed')
    if not json_path or not json_path.exists():
        print("Berkas dossier tidak ditemukan. Jalankan subcommand match terlebih dahulu.")
        return

    if dry_run:
        entities = json.loads(json_path.read_text(encoding='utf-8'))
        print(f"Dry-run ekspor: {len(entities)} baris dossier dari {json_path.name}")
        for ent in entities[:5]:
            print(f"  {ent.get('entity_id', '-')}: {ent.get('business_name', '-')} "
                  f"| Platform: {','.join(ent.get('platforms') or [])}")
        print("Mode dry-run aktif: berkas CSV tidak ditulis.")
        return

    csv_path = Path(output_path) if output_path else \
        PROJECT_ROOT / 'data' / 'processed' / f"dossiers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    entities = json.loads(json_path.read_text(encoding='utf-8'))
    written = export_dossiers_to_csv(entities, csv_path, require_whatsapp=not include_no_wa)
    print(f"Ekspor CSV selesai: {written}")


def run_harvest_pipeline(sector: str, limit_per_query: int, dry_run: bool):
    print(f"Menjalankan panen prospek Makassar (Sektor: {sector}, Limit/query: {limit_per_query}, Dry-run: {dry_run})")
    harvest(sector=sector, limit_per_query=limit_per_query, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(description="RUANG VISUAL Market Intelligence Pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Subcommand: gmaps
    gmaps_parser = subparsers.add_parser("gmaps", help="Jalankan scraper Google Maps")
    gmaps_parser.add_argument("--query", type=str, required=True, help="Kata kunci pencarian (misal: cafe, resto)")
    gmaps_parser.add_argument("--city", type=str, default="Makassar", help="Nama kota")
    gmaps_parser.add_argument("--limit", type=int, default=20, help="Jumlah tempat maksimal")
    gmaps_parser.add_argument("--dry-run", action="store_true", help="Uji coba tanpa panggilan berbayar")
    gmaps_parser.add_argument("--save-db", action="store_true", help="Simpan hasil ke database Supabase")
    
    # Subcommand: instagram
    ig_parser = subparsers.add_parser("instagram", help="Jalankan scraper Instagram")
    ig_parser.add_argument("--target", type=str, required=True, help="Username Instagram target")
    ig_parser.add_argument("--limit", type=int, default=50, help="Limit followers")
    ig_parser.add_argument("--dry-run", action="store_true", help="Uji coba tanpa panggilan berbayar")
    ig_parser.add_argument("--save-db", action="store_true", help="Simpan hasil ke database Supabase")
    
    # Subcommand: meta-ads
    meta_parser = subparsers.add_parser("meta-ads", help="Jalankan scraper Meta Ads Library")
    meta_parser.add_argument("--query", type=str, required=True, help="Kata kunci pencarian iklan")
    meta_parser.add_argument("--limit", type=int, default=50, help="Jumlah iklan maksimal")
    meta_parser.add_argument("--dry-run", action="store_true", help="Uji coba tanpa panggilan berbayar")
    meta_parser.add_argument("--save-db", action="store_true", help="Simpan hasil ke database Supabase")
    
    # Subcommand: tiktok
    tiktok_parser = subparsers.add_parser("tiktok", help="Jalankan scraper TikTok")
    tiktok_parser.add_argument("--keyword", type=str, required=True, help="Kata kunci pencarian TikTok")
    tiktok_parser.add_argument("--limit", type=int, default=20, help="Jumlah akun maksimal")
    tiktok_parser.add_argument("--dry-run", action="store_true", help="Uji coba tanpa panggilan berbayar")
    tiktok_parser.add_argument("--save-db", action="store_true", help="Simpan hasil ke database Supabase")

    # Subcommand: threads
    threads_parser = subparsers.add_parser("threads", help="Jalankan scraper Threads")
    threads_parser.add_argument("--username", type=str, required=True, help="Username Threads target")
    threads_parser.add_argument("--limit", type=int, default=10, help="Jumlah post maksimal")
    threads_parser.add_argument("--dry-run", action="store_true", help="Uji coba tanpa panggilan berbayar")
    threads_parser.add_argument("--save-db", action="store_true", help="Simpan hasil ke database Supabase")

    # Subcommand: food-delivery
    food_parser = subparsers.add_parser("food-delivery", help="Jalankan scraper Food Delivery Apps")
    food_parser.add_argument("--platform", type=str, required=True, choices=["gofood", "grabfood", "shopeefood"], help="Platform food delivery")
    food_parser.add_argument("--city", type=str, default="Makassar", help="Nama kota")
    food_parser.add_argument("--limit", type=int, default=20, help="Jumlah merchant maksimal")
    food_parser.add_argument("--dry-run", action="store_true", help="Uji coba tanpa panggilan berbayar")
    food_parser.add_argument("--save-db", action="store_true", help="Simpan hasil ke database Supabase")

    # Subcommand: match
    match_parser = subparsers.add_parser("match", help="Cocokkan entitas bisnis lintas platform menjadi dossier terpadu")
    match_parser.add_argument("--raw-dir", type=str, default="data/raw", help="Folder data mentah input")
    match_parser.add_argument("--output-dir", type=str, default="data/processed", help="Folder keluaran dossier terpadu")
    match_parser.add_argument("--city", type=str, default="Makassar", help="Label kota untuk penamaan berkas")
    match_parser.add_argument("--dry-run", action="store_true", help="Pratinjau hasil tanpa menulis berkas")
    match_parser.add_argument("--save-db", action="store_true", help="Sinkronkan dossier terpadu ke database Supabase")

    # Subcommand: export
    export_parser = subparsers.add_parser("export", help="Ekspor dossier terpadu ke berkas CSV")
    export_parser.add_argument("--input", type=str, default=None, help="Path berkas JSON dossier (default: berkas terbaru di data/processed)")
    export_parser.add_argument("--output", type=str, default=None, help="Path berkas CSV keluaran (default: data/processed/dossiers_export_<timestamp>.csv)")
    export_parser.add_argument("--dry-run", action="store_true", help="Tampilkan ringkasan baris tanpa menulis berkas")
    export_parser.add_argument("--include-no-wa", action="store_true", help="Sertakan entitas tanpa nomor WhatsApp di berkas utama")

    # Subcommand: dashboard
    subparsers.add_parser("dashboard", help="Buka dashboard visual lokal RUANG VISUAL di port 3000")

    # Subcommand: test
    subparsers.add_parser("test", help="Jalankan seluruh rangkaian unit test")

    # Subcommand: sync-db
    sync_parser = subparsers.add_parser("sync-db", help="Sinkronkan berkas dossier JSON ke database Supabase")
    sync_parser.add_argument("--input", type=str, default=None, help="Path berkas JSON dossier (default: berkas terbaru di data/processed)")
    sync_parser.add_argument("--dry-run", action="store_true", help="Simulasi sinkronisasi tanpa menulis ke database")

    # Subcommand: harvest
    harvest_parser = subparsers.add_parser("harvest", help="Panen massal prospek terarah per kecamatan di Makassar")
    harvest_parser.add_argument("--sector", choices=["fnb_hospitality", "retail_apparel", "education", "corporate_legal", "event_community", "beauty_skincare", "all"], default="all", help="Sektor bisnis target")
    harvest_parser.add_argument("--limit-per-query", type=int, default=5, help="Batas maksimal tempat per query")
    harvest_parser.add_argument("--dry-run", action="store_true", help="Simulasi tanpa pemanggilan berbayar")

    args = parser.parse_args()

    if args.command == "gmaps":
        run_gmaps_pipeline(args.query, args.city, args.limit, args.dry_run, args.save_db)
    elif args.command == "instagram":
        run_instagram_pipeline(args.target, args.limit, args.dry_run, args.save_db)
    elif args.command == "meta-ads":
        run_meta_ads_pipeline(args.query, args.limit, args.dry_run, args.save_db)
    elif args.command == "tiktok":
        run_tiktok_pipeline(args.keyword, args.limit, args.dry_run, args.save_db)
    elif args.command == "threads":
        run_threads_pipeline(args.username, args.limit, args.dry_run, args.save_db)
    elif args.command == "food-delivery":
        run_food_delivery_pipeline(args.platform, args.city, args.limit, args.dry_run, args.save_db)
    elif args.command == "match":
        run_match_pipeline(args.raw_dir, args.output_dir, args.city, args.dry_run, args.save_db)
    elif args.command == "export":
        run_export_pipeline(args.input, args.output, args.dry_run, getattr(args, 'include_no_wa', False))
    elif args.command == "dashboard":
        from scrapers.dashboard_server import start_server
        start_server()
    elif args.command == "test":
        import unittest
        loader = unittest.TestLoader()
        suite = loader.discover("tests")
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    elif args.command == "sync-db":
        json_path = Path(args.input) if args.input else find_latest_dossier(PROJECT_ROOT / 'data' / 'processed')
        if not json_path or not json_path.exists():
            print("Tidak ada berkas dossier yang ditemukan untuk disinkronkan.")
        else:
            dossiers = json.loads(Path(json_path).read_text(encoding='utf-8'))
            count, msg = batch_upsert_dossiers(dossiers, dry_run=args.dry_run)
            print(f"Input: {json_path} | Baris: {count}")
            print(msg)
    elif args.command == "harvest":
        run_harvest_pipeline(args.sector, args.limit_per_query, args.dry_run)


if __name__ == "__main__":
    main()
