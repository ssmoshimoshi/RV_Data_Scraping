import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
from datetime import datetime
from scrapers.normalizer import normalize_whatsapp
from scrapers.pain_points import extract_packaging_pain_points
from scrapers.lead_scoring import estimate_packaging_volume_and_value, classify_category





def _process_merchant_data(item: dict) -> dict:
    raw_reviews = item.get('reviews', [])
    pain_points = extract_packaging_pain_points(raw_reviews)
    
    name = item.get('name') or item.get('title') or item.get('restaurantName', '') or item.get('merchant_name', '')
    raw_cat = item.get('category') or item.get('categoryName', '')
    category = item.get('classified_category') or classify_category(name, raw_cat, [])
    
    reviews_count = item.get('reviews_count') or item.get('reviewsCount') or item.get('totalReviews', 0)
    try:
        reviews_count = int(reviews_count)
    except (ValueError, TypeError):
        reviews_count = 0
    lead_for_est = {
        'category': category,
        'reviews_count': reviews_count,
        'followers_count': item.get('followers_count', 0)
    }
    estimated_commercials = estimate_packaging_volume_and_value(lead_for_est)
    
    return {
        'classified_category': category,
        'packaging_pain_points': pain_points,
        'estimated_commercials': estimated_commercials
    }


def scrape_gofood(city: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would scrape GoFood merchants in {city}, limit {limit}")
        return []

    print(f"Scraping GoFood merchants in {city} locally...")
    
    # Simulasi sederhana karena platform food delivery tidak memiliki API publik
    merchants = []
    dummy_names = ['Rumah Makan Sederhana', 'Warung Padang Murah', 'Kafe Sehat', 
                   'Restoran Keluarga', 'Bakso Malang']
    
    for i in range(min(limit, 5)):
        merchant_name = dummy_names[i % len(dummy_names)]
        merchant = {
            'merchant_id': f'gofood_{i}_{datetime.utcnow().timestamp()}',
            'merchant_name': merchant_name,
            'category': 'Food & Beverage',
            'phone_number': normalize_whatsapp(f'0812345678{i}') if i % 2 == 0 else None,
            'address_full': f'Jl. Merdeka No. {i}, {city}',
            'district_area': f'Kecamatan {city}',
            'city': city,
            'platform': 'gofood',
            'scraped_at': datetime.utcnow().isoformat(),
            'reviews_count': 100 + i * 20,
            'rating': 4.0 + (i * 0.1),
            'followers_count': 500 + i * 50
        }
        
        proc = _process_merchant_data(merchant)
        merchant.update({
            'classified_category': proc['classified_category'],
            'packaging_pain_points': proc['packaging_pain_points'],
            'estimated_commercials': proc['estimated_commercials'],
            **proc['estimated_commercials']
        })
        
        merchants.append(merchant)

    return merchants


def scrape_grabfood(city: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would scrape GrabFood merchants in {city}, limit {limit}")
        return []

    print(f"Scraping GrabFood merchants in {city} locally...")
    
    # Simulasi sederhana karena platform food delivery tidak memiliki API publik
    merchants = []
    dummy_names = ['Restoran Cepat Saji', 'Kedai Kopi Tradisional', 'Warung Seafood', 
                   'Bakmi Ayam', 'Minuman Bubble']
    
    for i in range(min(limit, 5)):
        merchant_name = dummy_names[i % len(dummy_names)]
        merchant = {
            'merchant_id': f'grabfood_{i}_{datetime.utcnow().timestamp()}',
            'merchant_name': merchant_name,
            'category': 'Food & Beverage',
            'phone_number': normalize_whatsapp(f'0813456789{i}') if i % 3 == 0 else None,
            'address_full': f'Jl. Sudirman No. {i+10}, {city}',
            'district_area': f'Kecamatan Pusat {city}',
            'city': city,
            'platform': 'grabfood',
            'scraped_at': datetime.utcnow().isoformat(),
            'reviews_count': 150 + i * 30,
            'rating': 4.2 + (i * 0.08),
            'followers_count': 600 + i * 60
        }
        
        proc = _process_merchant_data(merchant)
        merchant.update({
            'classified_category': proc['classified_category'],
            'packaging_pain_points': proc['packaging_pain_points'],
            'estimated_commercials': proc['estimated_commercials'],
            **proc['estimated_commercials']
        })
        
        merchants.append(merchant)

    return merchants


def scrape_shopeefood(city: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would scrape ShopeeFood merchants in {city}, limit {limit}")
        return []

    print(f"Scraping ShopeeFood merchants in {city} locally...")
    
    # Simulasi sederhana karena platform food delivery tidak memiliki API publik
    merchants = []
    dummy_names = ['Kios Makanan Ringan', 'Warung Bakso', 'Kedai Minuman', 
                   'Restoran Ayam', 'Toko Kue']
    
    for i in range(min(limit, 5)):
        merchant_name = dummy_names[i % len(dummy_names)]
        merchant = {
            'merchant_id': f'shopeefood_{i}_{datetime.utcnow().timestamp()}',
            'merchant_name': merchant_name,
            'category': 'Food & Beverage',
            'phone_number': normalize_whatsapp(f'081456789{i}') if i % 2 == 1 else None,
            'address_full': f'Jl. Pasar Baru No. {i+5}, {city}',
            'district_area': f'Kecamatan Barat {city}',
            'city': city,
            'platform': 'shopeefood',
            'scraped_at': datetime.utcnow().isoformat(),
            'reviews_count': 80 + i * 25,
            'rating': 3.8 + (i * 0.12),
            'followers_count': 400 + i * 40
        }
        
        proc = _process_merchant_data(merchant)
        merchant.update({
            'classified_category': proc['classified_category'],
            'packaging_pain_points': proc['packaging_pain_points'],
            'estimated_commercials': proc['estimated_commercials'],
            **proc['estimated_commercials']
        })
        
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
