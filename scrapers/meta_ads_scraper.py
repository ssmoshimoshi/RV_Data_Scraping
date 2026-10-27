import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import re
from datetime import datetime
from typing import Optional, List, Dict
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


def search_meta_ads(query: str, limit: int = 50, dry_run: bool = False, country: str = 'ID') -> List[Dict]:
    if dry_run:
        print(f"[DRY RUN] Would search Meta Ads Library for '{query}' in {country}, limit {limit}")
        return []
    
    print(f"Mengumpulkan iklan Meta Ad Library untuk query '{query}' (Negara: {country}, Limit: {limit})...")
    try:
        from meta_ads_collector import MetaAdsCollector
        collector = MetaAdsCollector(timeout=30, max_retries=2)
        raw_ads = collector.collect(
            query=query,
            country=country,
            status="ACTIVE",
            max_results=limit
        )
    except Exception as e:
        print(f"Peringatan: Gagal mengambil iklan dari Meta Ads Collector: {e}")
        return []

    ads_data = []
    for item in raw_ads:
        page = getattr(item, 'page', None)
        page_id = getattr(page, 'page_id', None) or (page.get('page_id') if isinstance(page, dict) else None) or getattr(item, 'ad_library_id', None)
        page_name = getattr(page, 'page_name', None) or (page.get('page_name') if isinstance(page, dict) else '') or ''
        
        creatives = getattr(item, 'creatives', []) or []
        body_parts = []
        links_from_creatives = []
        for c in creatives:
            body = getattr(c, 'body', None)
            if body:
                body_parts.append(body)
            title = getattr(c, 'title', None)
            if title:
                body_parts.append(title)
            link_url = getattr(c, 'link_url', None)
            if link_url:
                links_from_creatives.append(link_url)
        
        ad_body = "\n".join(body_parts)
        whatsapp_number = extract_whatsapp_from_text(ad_body)
        external_links = extract_external_links(ad_body) + links_from_creatives
        unique_links = list(dict.fromkeys([l for l in external_links if l]))

        delivery_start = getattr(item, 'delivery_start_time', None)
        if isinstance(delivery_start, (int, float)):
            start_date_str = datetime.fromtimestamp(delivery_start).strftime("%Y-%m-%d")
        else:
            start_date_str = str(delivery_start) if delivery_start else None

        ad_dict = {
            'page_id': str(page_id) if page_id else '',
            'page_name': page_name,
            'ad_snapshot_url': getattr(item, 'snapshot_url', None) or getattr(item, 'ad_snapshot_url', None) or '',
            'ad_creative_body': ad_body,
            'ad_delivery_start_time': start_date_str,
            'publisher_platforms': getattr(item, 'publisher_platforms', []) or [],
            'whatsapp_number': whatsapp_number,
            'external_links': unique_links,
            'is_active': bool(getattr(item, 'is_active', True))
        }
        ads_data.append(ad_dict)
    
    print(f"Ditemukan {len(ads_data)} iklan aktif")
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
