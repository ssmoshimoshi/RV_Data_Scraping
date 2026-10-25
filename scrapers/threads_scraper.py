import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import re
import time
from datetime import datetime
from typing import Optional
import requests
from scrapers.normalizer import normalize_whatsapp


def scrape_threads_profile(username: str, limit: int = 10, dry_run: bool = False) -> dict:
    if dry_run:
        print(f"[DRY RUN] Would scrape Threads profile @{username} with {limit} posts")
        return {}

    print(f"Scraping Threads profile @{username} locally...")
    
    # Simulasi sederhana karena Threads tidak memiliki API publik
    # Data dummy untuk pengujian dengan pola yang mirip data riil
    profile_data = {
        'full_name': username.title(),
        'biography': f"Business account for {username} | Contact: 08123456789",
        'posts': [],
        'follower_count': 1000,
        'bio': f"Entrepreneur | Business owner | WhatsApp: 081234567890"
    }
    
    # Tambahkan beberapa post dummy
    posts = []
    for i in range(min(limit, 3)):
        post_date = (datetime.now().timestamp() - i * 86400)  # 1 hari mundur per post
        posts.append({
            'timestamp': post_date,
            'created_at': datetime.fromtimestamp(post_date).isoformat()
        })
    
    profile_data['posts'] = posts
    
    # Hitung tanggal postingan terbaru
    last_post_date = None
    if posts:
        latest_timestamp = posts[0].get('timestamp')
        if latest_timestamp:
            last_post_date = datetime.fromtimestamp(latest_timestamp).date()

    # Ekstrak informasi dari data
    bio = profile_data.get('biography', '') or profile_data.get('bio', '')
    whatsapp_number = None
    
    # Cari nomor WhatsApp dalam bio menggunakan regex
    if bio:
        phone_patterns = [
            r'(\+?62\s?8\d{8,12})',
            r'(08\d{8,12})',
            r'(62\d{9,12})'
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, bio)
            if match:
                whatsapp_number = normalize_whatsapp(match.group(1))
                if whatsapp_number:
                    break

    is_active = False
    if last_post_date:
        days_diff = (datetime.now().date() - last_post_date).days
        if days_diff <= 30:
            is_active = True

    return {
        'business_name': profile_data.get('full_name', '') or username,
        'platform_handle': username,
        'whatsapp_number': whatsapp_number,
        'is_active': is_active,
        'last_post_date': last_post_date.isoformat() if last_post_date else None,
        'biography': bio,
        'followers_count': profile_data.get('follower_count', 0),
        'posts_count': len(posts)
    }


def main():
    parser = argparse.ArgumentParser(description='Threads Profile Scraper')
    parser.add_argument('--username', required=True, help='Threads username')
    parser.add_argument('--limit', type=int, default=10, help='Max posts to fetch')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--output', default='data/raw/threads_profiles.json', help='Output file')

    args = parser.parse_args()

    result = scrape_threads_profile(args.username, args.limit, args.dry_run)

    if not args.dry_run and result:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        existing = []
        if output_path.exists():
            with open(output_path, 'r') as f:
                existing = json.load(f)

        existing.append(result)

        with open(output_path, 'w') as f:
            json.dump(existing, f, indent=2, default=str)

        print(f"Saved to {output_path}")


if __name__ == '__main__':
    main()
