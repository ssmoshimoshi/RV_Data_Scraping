import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import os
from datetime import datetime
from typing import Optional
from apify_client import ApifyClient
from dotenv import load_dotenv
from scrapers.normalizer import normalize_whatsapp, normalize_address

load_dotenv()


def scrape_gofood(city: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would scrape GoFood merchants in {city}, limit {limit}")
        return []

    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")

    client = ApifyClient(api_token)

    run_input = {
        "startUrls": [{"url": f"https://gofood.co.id/search?q={city}"}],
        "maxCrawlDepth": 1,
        "maxRequestsPerCrawl": limit
    }

    print(f"Scraping GoFood merchants in {city}...")
    run = client.actor("apify/web-scraper").call(run_input=run_input)

    merchants = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        name = item.get('name') or item.get('title', '')
        address = item.get('address', '')
        phone = item.get('phone') or item.get('phoneNumber')
        category = item.get('category', 'Food & Beverage')

        normalized_phone = normalize_whatsapp(phone) if phone else None
        address_data = normalize_address(address)

        merchant = {
            'merchant_id': item.get('id'),
            'merchant_name': name,
            'category': category,
            'phone_number': normalized_phone,
            'address_full': address_data['address_full'],
            'district_area': address_data['district_area'],
            'city': address_data['city'],
            'platform': 'gofood',
            'scraped_at': datetime.utcnow().isoformat()
        }
        merchants.append(merchant)

    return merchants


def scrape_grabfood(city: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would scrape GrabFood merchants in {city}, limit {limit}")
        return []

    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")

    client = ApifyClient(api_token)

    run_input = {
        "startUrls": [{"url": f"https://food.grab.com/id/id/search?q={city}"}],
        "maxCrawlDepth": 1,
        "maxRequestsPerCrawl": limit
    }

    print(f"Scraping GrabFood merchants in {city}...")
    run = client.actor("apify/web-scraper").call(run_input=run_input)

    merchants = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        name = item.get('name') or item.get('restaurantName', '')
        address = item.get('address', '')
        phone = item.get('phone') or item.get('phoneNumber')
        category = item.get('category', 'Food & Beverage')

        normalized_phone = normalize_whatsapp(phone) if phone else None
        address_data = normalize_address(address)

        merchant = {
            'merchant_id': item.get('id'),
            'merchant_name': name,
            'category': category,
            'phone_number': normalized_phone,
            'address_full': address_data['address_full'],
            'district_area': address_data['district_area'],
            'city': address_data['city'],
            'platform': 'grabfood',
            'scraped_at': datetime.utcnow().isoformat()
        }
        merchants.append(merchant)

    return merchants


def scrape_shopeefood(city: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would scrape ShopeeFood merchants in {city}, limit {limit}")
        return []

    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")

    client = ApifyClient(api_token)

    run_input = {
        "startUrls": [{"url": f"https://shopee.co.id/shopeefood/search?q={city}"}],
        "maxCrawlDepth": 1,
        "maxRequestsPerCrawl": limit
    }

    print(f"Scraping ShopeeFood merchants in {city}...")
    run = client.actor("apify/web-scraper").call(run_input=run_input)

    merchants = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        name = item.get('name') or item.get('title', '')
        address = item.get('address', '')
        phone = item.get('phone') or item.get('phoneNumber')
        category = item.get('category', 'Food & Beverage')

        normalized_phone = normalize_whatsapp(phone) if phone else None
        address_data = normalize_address(address)

        merchant = {
            'merchant_id': item.get('id'),
            'merchant_name': name,
            'category': category,
            'phone_number': normalized_phone,
            'address_full': address_data['address_full'],
            'district_area': address_data['district_area'],
            'city': address_data['city'],
            'platform': 'shopeefood',
            'scraped_at': datetime.utcnow().isoformat()
        }
        merchants.append(merchant)

    return merchants


def scrape_all(city: str, limit: int, dry_run: bool) -> dict:
    results = {
        'gofood': scrape_gofood(city, limit, dry_run),
        'grabfood': scrape_grabfood(city, limit, dry_run),
        'shopeefood': scrape_shopeefood(city, limit, dry_run)
    }
    return results


def save_results(data: dict, city: str, mode: str):
    output_dir = PROJECT_ROOT / 'data' / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"food_delivery_{city}_{mode}_{timestamp}.json"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Results saved to {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description='Scrape food delivery merchants')
    parser.add_argument('--city', type=str, default='Makassar', help='Target city')
    parser.add_argument('--mode', type=str, choices=['gofood', 'grabfood', 'shopeefood', 'all'], default='all')
    parser.add_argument('--limit', type=int, default=50, help='Max merchants per platform')
    parser.add_argument('--dry-run', action='store_true', help='Test without scraping')

    args = parser.parse_args()

    if args.mode == 'all':
        results = scrape_all(args.city, args.limit, args.dry_run)
    elif args.mode == 'gofood':
        results = {'gofood': scrape_gofood(args.city, args.limit, args.dry_run)}
    elif args.mode == 'grabfood':
        results = {'grabfood': scrape_grabfood(args.city, args.limit, args.dry_run)}
    else:
        results = {'shopeefood': scrape_shopeefood(args.city, args.limit, args.dry_run)}

    if not args.dry_run:
        save_results(results, args.city, args.mode)

    total = sum(len(v) for v in results.values())
    print(f"Total merchants scraped: {total}")


if __name__ == '__main__':
    main()
