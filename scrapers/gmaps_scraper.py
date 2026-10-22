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


def search_places(query: str, city: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would search Google Maps for '{query}' in {city}, limit {limit}")
        return []
    
    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")
    
    client = ApifyClient(api_token)
    
    search_query = f"{query} in {city}"
    
    run_input = {
        "searchStringsArray": [search_query],
        "maxCrawledPlacesPerSearch": limit,
        "language": "id"
    }
    
    print(f"Starting Apify actor: compass/crawler-google-places for '{search_query}'...")
    run = client.actor("compass/crawler-google-places").call(run_input=run_input)
    
    places = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        raw_phone = item.get('phone')
        raw_address = item.get('address', '')
        
        normalized_phone = normalize_whatsapp(raw_phone) if raw_phone else None
        address_data = normalize_address(raw_address)
        
        place_dict = {
            'place_id': item.get('placeId'),
            'title': item.get('title'),
            'category_name': item.get('categoryName', ''),
            'address': address_data['address_full'],
            'district_area': address_data['district_area'],
            'city': address_data['city'],
            'phone_number': raw_phone,
            'whatsapp_number': normalized_phone,
            'latitude': item.get('location', {}).get('lat'),
            'longitude': item.get('location', {}).get('lng'),
            'reviews_count': item.get('reviewsCount', 0),
            'total_score': item.get('totalScore', 0.0),
            'website': item.get('website')
        }
        places.append(place_dict)
    
    print(f"Found {len(places)} places")
    return places


def scrape_negative_reviews(place_id: str, max_stars: int = 3, dry_run: bool = False) -> list[str]:
    if dry_run:
        print(f"[DRY RUN] Would scrape negative reviews (<=stars) for place_id {place_id}")
        return []
    
    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")
    
    client = ApifyClient(api_token)
    
    run_input = {
        "startUrls": [{"url": f"https://www.google.com/maps/place/?q=place_id:{place_id}"}],
        "maxReviews": 100,
        "reviewsSort": "newest"
    }
    
    print(f"Fetching reviews for place_id {place_id}...")
    run = client.actor("compass/crawler-google-places").call(run_input=run_input)
    
    negative_reviews = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        reviews = item.get('reviews', [])
        for review in reviews:
            if review.get('stars', 5) <= max_stars and review.get('text'):
                negative_reviews.append(review['text'])
    
    print(f"Found {len(negative_reviews)} negative reviews")
    return negative_reviews


def main():
    parser = argparse.ArgumentParser(description='Google Maps Scraper Module')
    parser.add_argument('--mode', choices=['search', 'reviews'], required=True)
    parser.add_argument('--query', type=str, help='Search query')
    parser.add_argument('--city', type=str, help='City name')
    parser.add_argument('--place-id', type=str, help='Place ID for review mode')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--dry-run', action='store_true')
    
    args = parser.parse_args()
    
    output_dir = PROJECT_ROOT / 'data' / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.mode == 'search':
        if not args.query or not args.city:
            print("Error: --query and --city required for search mode")
            return
        
        places = search_places(args.query, args.city, args.limit, args.dry_run)
        
        if not args.dry_run:
            output_file = output_dir / f'gmaps_places_{args.city}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(places, f, indent=2, ensure_ascii=False)
            print(f"Saved to {output_file}")
    
    elif args.mode == 'reviews':
        if not args.place_id:
            print("Error: --place-id required for reviews mode")
            return
        
        reviews = scrape_negative_reviews(args.place_id, dry_run=args.dry_run)
        
        if not args.dry_run:
            output_file = output_dir / f'gmaps_reviews_{args.place_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({'place_id': args.place_id, 'negative_reviews': reviews}, f, indent=2, ensure_ascii=False)
            print(f"Saved to {output_file}")


if __name__ == '__main__':
    main()
