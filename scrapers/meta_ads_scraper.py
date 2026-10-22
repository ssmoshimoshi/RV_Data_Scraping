import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import os
import re
from datetime import datetime
from typing import Optional, List, Dict
from apify_client import ApifyClient
from dotenv import load_dotenv
from scrapers.normalizer import normalize_whatsapp

load_dotenv()


def extract_whatsapp_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    
    patterns = [
        r'(?:wa|whatsapp|hubungi|call|kontak)[\s:]*([+\d\s\-()]{10,20})',
        r'(?:^|\s)([+]?62\s*8[\d\s\-()]{9,15})',
        r'(?:^|\s)(08[\d\s\-()]{9,12})',
        r'(?:nomor|number|hp|phone)[\s:]*([+\d\s\-()]{10,20})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_number = match.group(1)
            normalized = normalize_whatsapp(raw_number)
            if normalized:
                return normalized
    
    return None


def extract_external_links(text: str) -> List[str]:
    if not text:
        return []
    
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    links = re.findall(url_pattern, text)
    return [link.rstrip('.,;:()') for link in links]


def search_meta_ads(query: str, limit: int, dry_run: bool, country: str = 'ID') -> List[Dict]:
    if dry_run:
        print(f"[DRY RUN] Would search Meta Ads Library for '{query}' in {country}, limit {limit}")
        return []
    
    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")
    
    client = ApifyClient(api_token)
    
    run_input = {
        "searchTerms": [query],
        "country": country,
        "resultsLimit": limit,
        "adActiveStatus": "ACTIVE"
    }
    
    print(f"Starting Apify actor: dtrungtin/facebook-ads-scraper for '{query}'...")
    run = client.actor("dtrungtin/facebook-ads-scraper").call(run_input=run_input)
    
    ads_data = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        ad_body = item.get('adCreativeBody', '') or item.get('text', '')
        
        whatsapp_number = extract_whatsapp_from_text(ad_body)
        external_links = extract_external_links(ad_body)
        
        ad_dict = {
            'page_id': item.get('pageID') or item.get('page_id'),
            'page_name': item.get('pageName') or item.get('page_name'),
            'ad_snapshot_url': item.get('adSnapshotURL') or item.get('ad_snapshot_url'),
            'ad_creative_body': ad_body,
            'ad_delivery_start_time': item.get('adDeliveryStartTime') or item.get('startDate'),
            'publisher_platforms': item.get('publisherPlatforms', []),
            'whatsapp_number': whatsapp_number,
            'external_links': external_links,
            'raw_data': item
        }
        ads_data.append(ad_dict)
    
    print(f"Found {len(ads_data)} active ads")
    return ads_data


def main():
    parser = argparse.ArgumentParser(description='Meta Ads Library Scraper Module')
    parser.add_argument('--mode', choices=['search'], required=True)
    parser.add_argument('--query', type=str, required=True, help='Search query (e.g., kuliner, coffee shop)')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--country', type=str, default='ID', help='Country code (default: ID)')
    
    args = parser.parse_args()
    
    output_dir = PROJECT_ROOT / 'data' / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.mode == 'search':
        ads = search_meta_ads(args.query, args.limit, args.dry_run, args.country)
        
        if not args.dry_run:
            safe_query = re.sub(r'[^\w\s-]', '', args.query).replace(' ', '_')
            output_file = output_dir / f'meta_ads_{safe_query}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(ads, f, indent=2, ensure_ascii=False)
            print(f"Saved to {output_file}")


if __name__ == '__main__':
    main()
