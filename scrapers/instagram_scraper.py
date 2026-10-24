import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from apify_client import ApifyClient
from dotenv import load_dotenv
from scrapers.normalizer import normalize_whatsapp, normalize_address

load_dotenv()


def _extract_dataset_id(run) -> str:
    if run is None:
        return ""
    if isinstance(run, dict):
        return run.get("defaultDatasetId") or run.get("default_dataset_id", "")
    return getattr(run, "default_dataset_id", "") or getattr(run, "defaultDatasetId", "")


def run_follower_spider(target_handle: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would fetch {limit} followers from @{target_handle}")
        return []
    
    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")
    
    client = ApifyClient(api_token)
    
    run_input = {
        "username": [target_handle],
        "resultsLimit": limit
    }
    
    print(f"Starting Apify actor: apify/instagram-followers-scraper for @{target_handle}...")
    run = client.actor("apify/instagram-followers-scraper").call(run_input=run_input)
    
    results = []
    dataset_id = _extract_dataset_id(run)
    for item in client.dataset(dataset_id).iterate_items():
        results.append(item)
    
    print(f"Fetched {len(results)} followers from @{target_handle}")
    return results


def enrich_profile(username: str, dry_run: bool = False) -> dict:
    if dry_run:
        print(f"[DRY RUN] Would enrich profile @{username}")
        return {}
    
    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found in environment")
    
    client = ApifyClient(api_token)
    
    run_input = {
        "usernames": [username],
        "resultsLimit": 1
    }
    
    print(f"Enriching profile @{username} via Apify actor...")
    run = client.actor("apify/instagram-profile-scraper").call(run_input=run_input)
    
    profile_data = {}
    dataset_id = _extract_dataset_id(run)
    for item in client.dataset(dataset_id).iterate_items():
        profile_data = item
        break
    
    raw_phone = profile_data.get('businessPhoneNumber') or profile_data.get('phoneNumber')
    normalized_phone = normalize_whatsapp(raw_phone) if raw_phone else None
    
    enriched = {
        'username': username,
        'business_phone_number': raw_phone,
        'whatsapp_number': normalized_phone,
        'biography': profile_data.get('biography', ''),
        'external_url': profile_data.get('externalUrl', ''),
        'followers_count': profile_data.get('followersCount', 0),
        'latest_post_timestamps': []
    }
    
    posts = profile_data.get('latestPosts', [])
    if posts:
        enriched['latest_post_timestamps'] = [
            post.get('timestamp') for post in posts[:3] if post.get('timestamp')
        ]
    
    return enriched


def validate_recency(profile: dict, max_days: int = 30) -> bool:
    timestamps = profile.get('latest_post_timestamps', [])
    if not timestamps:
        return False
    
    latest_timestamp = timestamps[0]
    if isinstance(latest_timestamp, str):
        try:
            latest_date = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
        except:
            return False
    elif isinstance(latest_timestamp, (int, float)):
        latest_date = datetime.fromtimestamp(latest_timestamp)
    else:
        return False
    
    days_ago = (datetime.now() - latest_date).days
    return days_ago <= max_days


def main():
    parser = argparse.ArgumentParser(description='Instagram Scraper Module')
    parser.add_argument('--mode', choices=['followers', 'enrich'], required=True)
    parser.add_argument('--target', type=str, help='Target username')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--dry-run', action='store_true')
    
    args = parser.parse_args()
    
    output_dir = PROJECT_ROOT / 'data' / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.mode == 'followers':
        if not args.target:
            print("Error: --target required for followers mode")
            return
        
        results = run_follower_spider(args.target, args.limit, args.dry_run)
        
        if not args.dry_run:
            output_file = output_dir / f'instagram_followers_{args.target}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Saved to {output_file}")
    
    elif args.mode == 'enrich':
        if not args.target:
            print("Error: --target required for enrich mode")
            return
        
        profile = enrich_profile(args.target, args.dry_run)
        
        if not args.dry_run:
            is_recent = validate_recency(profile)
            profile['is_active'] = is_recent
            
            output_file = output_dir / f'instagram_profile_{args.target}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            print(f"Profile active: {is_recent}")
            print(f"Saved to {output_file}")


if __name__ == '__main__':
    main()
