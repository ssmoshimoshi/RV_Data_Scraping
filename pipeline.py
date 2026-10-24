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
from scrapers.lead_scoring import qualify_lead, calculate_score, classify_category
from scrapers.database import insert_lead, get_supabase_client


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
        print(f"Prospek lolos: {lead['business_name']} | Kategori: {category} | Skor: {score}")
        
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
            "category": classify_category(item.get("merchant_name", ""), item.get("category", ""), []),
            "is_active_verified": True
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

    # Subcommand: test
    subparsers.add_parser("test", help="Jalankan seluruh rangkaian unit test")

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
    elif args.command == "test":
        import unittest
        loader = unittest.TestLoader()
        suite = loader.discover("tests")
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)


if __name__ == "__main__":
    main()
