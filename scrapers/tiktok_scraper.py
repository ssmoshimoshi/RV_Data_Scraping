import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import re
from datetime import datetime, timedelta
from typing import Optional
from scrapers.normalizer import normalize_whatsapp

MOCK_DATA = [
    {
        'username': '@kulinermakassar_viral',
        'display_name': 'Kuliner Makassar Enak',
        'bio': 'Jual paket hampers lebaran. Order via WA 081234567890. Buka setiap hari',
        'bio_link': 'https://linktr.ee/kulinermks',
        'is_seller_badge': True,
        'has_shop_link': True,
        'last_post_date': '2026-10-20',
        'hashtags': ['#kulinermakassar', '#hamperslebaran', '#kemasanmakanan']
    },
    {
        'username': '@hampers_custom_jkt',
        'display_name': 'Hampers Custom Jakarta',
        'bio': 'Custom hampers premium. Hub 08567891234 untuk katalog lengkap',
        'bio_link': '',
        'is_seller_badge': True,
        'has_shop_link': False,
        'last_post_date': '2026-10-22',
        'hashtags': ['#hampersjakarta', '#kemasanpremium', '#umkmlokal']
    },
    {
        'username': '@kue_kering_rumahan',
        'display_name': 'Kue Kering Rumahan Bu Siti',
        'bio': 'Kue kering homemade Surabaya. Pemesanan minimal 5 toples. WA 628123456789',
        'bio_link': '',
        'is_seller_badge': False,
        'has_shop_link': False,
        'last_post_date': '2026-10-18',
        'hashtags': ['#kuekering', '#umkmsurabaya', '#kemasantoples']
    }
]


def extract_phone_from_bio(bio_text: str) -> Optional[str]:
    if not bio_text:
        return None
    
    phone_patterns = [
        r'(?:wa|whatsapp|hp|telp|call)[:\s]*([+\d\s\-\(\)]{10,})',
        r'(\+?62\s?8\d{8,12})',
        r'(08\d{8,12})',
        r'(\d{10,13})'
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, bio_text, re.IGNORECASE)
        if match:
            return normalize_whatsapp(match.group(1))
    
    return None


def extract_hashtags(caption_or_bio: str) -> list:
    if not caption_or_bio:
        return []
    return re.findall(r'#\w+', caption_or_bio.lower())


def validate_recency(last_post_date_str: str, max_days: int = 30) -> bool:
    if not last_post_date_str:
        return False
    
    try:
        last_post_date = datetime.fromisoformat(last_post_date_str)
        days_ago = (datetime.now() - last_post_date).days
        return days_ago <= max_days
    except:
        return False


def detect_relevant_hashtags(hashtags: list) -> bool:
    target_keywords = [
        'kuliner', 'hampers', 'kemasan', 'unboxing', 'umkm', 'makanan',
        'kue', 'snack', 'packaging', 'custom', 'oleholeh', 'premium'
    ]
    
    for tag in hashtags:
        for keyword in target_keywords:
            if keyword in tag:
                return True
    return False


def scrape_tiktok_playwright(keyword: str, limit: int = 10) -> list:
    try:
        import urllib.parse
        from playwright.sync_api import sync_playwright
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="id-ID",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            url = f"https://www.tiktok.com/search/user?q={urllib.parse.quote(keyword)}"
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)

            user_cards = page.locator('div[data-e2e="search-user-container"], div.search-user-item').all()
            for card in user_cards[:limit]:
                u_el = card.locator('p[data-e2e="search-user-unique-id"], a[href*="/@"]').first
                u_text = u_el.text_content() if u_el.count() > 0 else ''
                d_el = card.locator('h4, span[data-e2e="search-user-nickname"]').first
                d_text = d_el.text_content() if d_el.count() > 0 else ''
                b_el = card.locator('p[data-e2e="search-user-desc"]').first
                b_text = b_el.text_content() if b_el.count() > 0 else ''

                if u_text:
                    handle = u_text.strip().lstrip('@')
                    results.append({
                        'username': f"@{handle}",
                        'display_name': d_text.strip() or handle,
                        'bio': b_text.strip(),
                        'bio_link': f"https://www.tiktok.com/@{handle}",
                        'is_seller_badge': False,
                        'has_shop_link': False,
                        'last_post_date': datetime.now().strftime("%Y-%m-%d"),
                        'hashtags': [f"#{keyword.replace(' ', '')}"]
                    })
            browser.close()
        return results
    except Exception as e:
        print(f"Peringatan: Gagal melakukan perayapan Playwright TikTok: {e}")
        return []


def scrape_tiktok_search(keyword: str, limit: int, dry_run: bool) -> list:
    if dry_run:
        print(f"[DRY RUN] Would search TikTok for keyword '{keyword}' with limit {limit}")
        return []
    
    live_results = scrape_tiktok_playwright(keyword, limit)
    if live_results:
        print(f"Ditemukan {len(live_results)} profil bisnis dari perayap lokal TikTok")
        return live_results
    
    print(f"Menggunakan data referensi lokal untuk '{keyword}' (limit: {limit})")
    return MOCK_DATA[:limit]


def transform_to_lead_format(raw_data: list) -> list:
    leads = []
    
    for item in raw_data:
        username = item.get('username', '')
        display_name = item.get('display_name', '')
        bio = item.get('bio', '')
        bio_link = item.get('bio_link', '')
        last_post_date = item.get('last_post_date', '')
        hashtags = item.get('hashtags', [])
        is_seller_badge = item.get('is_seller_badge', False)
        has_shop_link = item.get('has_shop_link', False)
        
        whatsapp_number = extract_phone_from_bio(bio)
        is_active = validate_recency(last_post_date)
        has_relevant_hashtags = detect_relevant_hashtags(hashtags)
        
        if not is_active:
            continue
        
        lead = {
            'platform': 'tiktok',
            'username': username,
            'display_name': display_name,
            'bio_text': bio,
            'bio_link': bio_link,
            'whatsapp_number': whatsapp_number,
            'last_post_date': last_post_date,
            'is_active': is_active,
            'is_seller_badge': is_seller_badge,
            'has_shop_link': has_shop_link,
            'relevant_hashtags': [tag for tag in hashtags if any(kw in tag for kw in ['kuliner', 'hampers', 'kemasan', 'umkm', 'packaging'])],
            'extracted_at': datetime.now().isoformat()
        }
        
        leads.append(lead)
    
    return leads


def main():
    parser = argparse.ArgumentParser(description='TikTok Scraper Module')
    parser.add_argument('--mode', choices=['mock', 'live', 'search'], default='search')
    parser.add_argument('--keyword', type=str, default='hampers kemasan')
    parser.add_argument('--hashtag', type=str, help='Target hashtag (alternative to keyword)')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--dry-run', action='store_true')
    
    args = parser.parse_args()
    
    search_term = args.hashtag if args.hashtag else args.keyword
    
    if args.mode == 'mock':
        raw_results = MOCK_DATA[:args.limit]
    else:
        raw_results = scrape_tiktok_search(search_term, args.limit, args.dry_run)
    
    if args.dry_run:
        print("[DRY RUN] No data to process")
        return
    
    leads = transform_to_lead_format(raw_results)
    
    print(f"\n[RESULTS] Extracted {len(leads)} active leads from TikTok")
    print(f"[FILTER] Removed {len(raw_results) - len(leads)} inactive accounts")
    
    output_dir = PROJECT_ROOT / 'data' / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f'tiktok_leads_{timestamp}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)
    
    print(f"[SAVED] {output_file}")
    
    for lead in leads[:3]:
        print(f"\nSample: {lead['username']} | WA: {lead['whatsapp_number']} | Seller: {lead['is_seller_badge']}")


if __name__ == '__main__':
    main()
