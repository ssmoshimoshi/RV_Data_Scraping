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

from dotenv import load_dotenv
from scrapers.normalizer import normalize_whatsapp

load_dotenv()


def _extract_json_data(html: str) -> dict:
    pattern = r'<script type="application/ld\+json">({.*?})</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match)
            if data.get('@type') == 'ProfilePage':
                return data
        except Exception:
            continue
    
    pattern = r'window\._sharedData = ({.*?});</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match)
        except Exception:
            continue
    return {}


def scrape_instagram_profile_http(username: str) -> dict:
    try:
        from curl_cffi import requests
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        url = f'https://www.instagram.com/{username}/'
        response = requests.get(url, headers=headers, timeout=30, impersonate='chrome120')
        
        if response.status_code == 404:
            return {'error': 'Profile not found', 'username': username}
        
        html = response.text
        json_data = _extract_json_data(html)
        
        result = {
            'username': username,
            'full_name': '',
            'biography': '',
            'external_url': None,
            'followers_count': 0,
            'following_count': 0,
            'posts_count': 0,
            'is_business_account': False,
            'is_verified': False,
            'profile_pic_url': '',
            'recent_posts': [],
        }
        
        if '@type' in json_data and json_data.get('@type') == 'ProfilePage':
            main_entity = json_data.get('mainEntity', {})
            result['full_name'] = main_entity.get('name', '')
            result['biography'] = main_entity.get('description', '')
            
            interactions = main_entity.get('interactionStatistic', [])
            for stat in interactions:
                if not isinstance(stat, dict):
                    continue
                interaction_type = stat.get('interactionType', '')
                if 'FollowAction' in interaction_type:
                    result['followers_count'] = stat.get('userInteractionCount', 0)
        
        if 'entry_data' in json_data:
            profile_page = json_data.get('entry_data', {}).get('ProfilePage', [])
            if profile_page:
                user = profile_page[0].get('graphql', {}).get('user', {})
                result['full_name'] = user.get('full_name', '')
                result['biography'] = user.get('biography', '')
                result['external_url'] = user.get('external_url')
                result['followers_count'] = user.get('edge_followed_by', {}).get('count', 0)
                result['following_count'] = user.get('edge_follow', {}).get('count', 0)
                result['posts_count'] = user.get('edge_owner_to_timeline_media', {}).get('count', 0)
                result['is_business_account'] = user.get('is_business_account', False)
                result['is_verified'] = user.get('is_verified', False)
                result['profile_pic_url'] = user.get('profile_pic_url_hd', '')
                
                edges = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
                for edge in edges[:10]:
                    node = edge.get('node', {})
                    post = {
                        'shortcode': node.get('shortcode', ''),
                        'caption': '',
                        'likes': node.get('edge_liked_by', {}).get('count', 0),
                        'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                        'timestamp': node.get('taken_at_timestamp', 0),
                    }
                    caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                    if caption_edges:
                        post['caption'] = caption_edges[0].get('node', {}).get('text', '')
                    result['recent_posts'].append(post)
        
        return result
    except Exception as e:
        return {'error': str(e), 'username': username}


def try_instagrapi_business_phone(username: str, session_file: Optional[Path] = None) -> Optional[str]:
    try:
        from instagrapi import Client
        
        if not session_file or not session_file.exists():
            return None
        
        cl = Client()
        cl.load_settings(session_file)
        
        user_id = cl.user_id_from_username(username)
        user_info = cl.user_info(user_id)
        
        return user_info.public_phone_number or user_info.contact_phone_number
    except Exception:
        return None


def enrich_profile(username: str, dry_run: bool = False) -> dict:
    if dry_run:
        print(f"[DRY RUN] Would fetch Instagram profile for @{username}")
        return {}
    
    print(f"Fetching Instagram profile for @{username}...")
    profile = scrape_instagram_profile_http(username)
    
    if profile.get('error'):
        print(f"Error: {profile['error']}")
        return profile
    
    session_file = PROJECT_ROOT / 'data' / 'instagram_session.json'
    business_phone = try_instagrapi_business_phone(username, session_file)
    if business_phone:
        profile['business_phone_number'] = business_phone
        profile['whatsapp_number'] = normalize_whatsapp(business_phone)
    
    external_url = profile.get('external_url', '')
    if external_url:
        wa_match = re.search(r'(?:wa\.me/|whatsapp\.com/send\?phone=)(\d+)', external_url)
        if wa_match:
            raw_wa = wa_match.group(1)
            profile['whatsapp_number'] = normalize_whatsapp(raw_wa)
    
    print(f"Profile fetched: {profile.get('full_name', username)} (@{username})")
    print(f"  Followers: {profile.get('followers_count', 0):,}")
    print(f"  Posts: {profile.get('posts_count', 0)}")
    
    return profile


def validate_recency(profile: dict, max_days: int = 30) -> bool:
    timestamps = profile.get('latest_post_timestamps', [])
    if not timestamps:
        recent_posts = profile.get('recent_posts', [])
        if recent_posts:
            return True
        return False
    
    latest_timestamp = timestamps[0]
    if isinstance(latest_timestamp, str):
        try:
            latest_date = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
        except Exception:
            return False
    elif isinstance(latest_timestamp, (int, float)):
        latest_date = datetime.fromtimestamp(latest_timestamp)
    else:
        return False
    
    days_ago = (datetime.now() - latest_date).days
    return days_ago <= max_days


def run_follower_spider(target_handle: str, limit: int, dry_run: bool) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would fetch {limit} followers from @{target_handle}")
        return []
    
    print(f"Fetching followers from @{target_handle} (limit: {limit})...")
    print("Note: Follower scraping requires instagrapi with authenticated session.")
    
    session_file = PROJECT_ROOT / 'data' / 'instagram_session.json'
    
    try:
        from instagrapi import Client
        
        if not session_file.exists():
            print(f"Session file not found at {session_file}. Cannot fetch followers.")
            return []
        
        cl = Client()
        cl.load_settings(session_file)
        
        user_id = cl.user_id_from_username(target_handle)
        followers = cl.user_followers(user_id, amount=limit)
        
        results = []
        for user_id, user_info in followers.items():
            results.append({
                'username': user_info.username,
                'full_name': user_info.full_name,
                'is_private': user_info.is_private,
                'is_verified': user_info.is_verified,
                'follower_count': user_info.follower_count,
            })
        
        print(f"Fetched {len(results)} followers from @{target_handle}")
        return results
    except ImportError:
        print("instagrapi not installed. Install with: pip install instagrapi")
        return []
    except Exception as e:
        print(f"Error fetching followers: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='Instagram Scraper Module')
    parser.add_argument('--target', type=str, help='Instagram username target')
    parser.add_argument('--limit', type=int, default=100, help='Limit for follower fetch')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--mode', choices=['profile', 'followers'], default='profile')
    
    args = parser.parse_args()
    
    if not args.target:
        print("Error: --target required")
        return
    
    output_dir = PROJECT_ROOT / 'data' / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.mode == 'profile':
        profile = enrich_profile(args.target, args.dry_run)
        
        if not args.dry_run and profile and not profile.get('error'):
            output_file = output_dir / f'instagram_{args.target}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            print(f"Saved to {output_file}")
    
    elif args.mode == 'followers':
        followers = run_follower_spider(args.target, args.limit, args.dry_run)
        
        if not args.dry_run and followers:
            output_file = output_dir / f'instagram_followers_{args.target}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(followers, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(followers)} followers to {output_file}")


if __name__ == '__main__':
    main()
