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
from typing import Optional
from apify_client import ApifyClient
from dotenv import load_dotenv
from scrapers.normalizer import normalize_whatsapp

load_dotenv()


def scrape_threads_profile(username: str, limit: int = 10, dry_run: bool = False) -> dict:
    if dry_run:
        print(f"[DRY RUN] Would scrape Threads profile @{username} with {limit} posts")
        return {}

    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")

    client = ApifyClient(api_token)

    run_input = {
        "usernames": [username],
        "maxPosts": limit
    }

    print(f"Scraping Threads profile @{username}...")
    run = client.actor("apify/threads-scraper").call(run_input=run_input)

    profile_data = {}
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        profile_data = item
        break

    posts = profile_data.get('posts', [])
    last_post_date = None
    if posts:
        latest_timestamp = posts[0].get('timestamp') or posts[0].get('created_at')
        if latest_timestamp:
            if isinstance(latest_timestamp, str):
                try:
                    last_post_date = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00')).date()
                except:
                    pass
            elif isinstance(latest_timestamp, (int, float)):
                last_post_date = datetime.fromtimestamp(latest_timestamp).date()

    bio = profile_data.get('biography', '') or profile_data.get('bio', '')
    raw_phone = profile_data.get('phone_number') or profile_data.get('contact_phone_number')
    whatsapp_number = normalize_whatsapp(raw_phone) if raw_phone else None
    
    if not whatsapp_number and bio:
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
