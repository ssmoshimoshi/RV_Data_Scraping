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
    
    # Subcommand: test
    subparsers.add_parser("test", help="Jalankan seluruh rangkaian unit test")
    
    args = parser.parse_args()
    
    if args.command == "gmaps":
        run_gmaps_pipeline(args.query, args.city, args.limit, args.dry_run, args.save_db)
    elif args.command == "instagram":
        run_instagram_pipeline(args.target, args.limit, args.dry_run, args.save_db)
    elif args.command == "test":
        import unittest
        loader = unittest.TestLoader()
        suite = loader.discover("tests")
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)


if __name__ == "__main__":
    main()
