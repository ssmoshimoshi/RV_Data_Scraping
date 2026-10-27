import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import os
import re
import urllib.parse
from datetime import datetime

from dotenv import load_dotenv

from scrapers.normalizer import normalize_whatsapp, normalize_address
from scrapers.pain_points import extract_packaging_pain_points
from scrapers.lead_scoring import estimate_packaging_volume_and_value, classify_category

load_dotenv()

_PLACE_ID_PATTERN = re.compile(r'(?:place_id:|!1s)(ChIJ[a-zA-Z0-9_\-]+)')


def _extract_place_id_from_url(url: str) -> str:
    if not url:
        return ""
    m = _PLACE_ID_PATTERN.search(url)
    if m:
        return m.group(1)
    return ""


def _is_low_rating(review: dict) -> bool:
    if not isinstance(review, dict):
        return True
    stars = review.get('stars') if review.get('stars') is not None else review.get('rating')
    if stars is None:
        return True
    try:
        return float(stars) <= 3.0
    except (ValueError, TypeError):
        return True


def _process_listing_data(item: dict) -> dict:
    raw_reviews = item.get('reviews') or []
    negative_reviews = [r for r in raw_reviews if _is_low_rating(r)]
    reviews_to_analyze = negative_reviews if negative_reviews else raw_reviews
    pain_points = extract_packaging_pain_points(reviews_to_analyze)

    title = (item.get('title') or item.get('name') or '').strip()
    category_name = (item.get('categoryName') or item.get('category_name') or '').strip()
    category = item.get('category') or classify_category(title, category_name, [])

    reviews_count = item.get('reviews_count') if item.get('reviews_count') is not None else item.get('reviewsCount', 0)
    try:
        reviews_count = int(reviews_count)
    except (ValueError, TypeError):
        reviews_count = 0

    followers_count = item.get('followers_count', 0)

    lead_for_est = {
        'category': category,
        'reviews_count': reviews_count,
        'followers_count': followers_count
    }

    return {
        'category': category,
        'reviews': raw_reviews,
        'packaging_pain_points': pain_points,
        'estimated_commercials': estimate_packaging_volume_and_value(lead_for_est)
    }


def _get_browser(playwright):
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    try:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        return browser
    except Exception:
        pass
    try:
        if os.path.exists(chrome_path):
            browser = playwright.chromium.launch(executable_path=chrome_path, headless=True)
            return browser
    except Exception:
        pass
    try:
        browser = playwright.chromium.launch(headless=True)
        return browser
    except Exception as e:
        raise RuntimeError(f"Tidak dapat menjalankan browser Playwright: {e}")


def parse_place_entry(item: dict, default_city: str = "Makassar") -> dict:
    title = (item.get('title') or item.get('name') or '').strip()
    category_name = (item.get('categoryName') or item.get('category_name') or '').strip()

    raw_address = item.get('address') or ''
    address_data = normalize_address(raw_address)
    city = address_data.get('city') or item.get('city') or default_city

    raw_phone = item.get('phone') or item.get('phone_number') or item.get('phoneNumber') or ''
    whatsapp = normalize_whatsapp(raw_phone) if raw_phone else None

    reviews_count = item.get('reviewsCount') if item.get('reviewsCount') is not None else item.get('reviews_count', 0)
    try:
        reviews_count = int(reviews_count)
    except (ValueError, TypeError):
        reviews_count = 0

    total_score = item.get('totalScore') if item.get('totalScore') is not None else item.get('total_score', 0.0)
    try:
        total_score = float(total_score)
    except (ValueError, TypeError):
        total_score = 0.0

    listing_proc = _process_listing_data(item)
    category = listing_proc['category']
    raw_reviews = listing_proc['reviews']
    pain_points = listing_proc['packaging_pain_points']
    estimated_commercials = listing_proc['estimated_commercials']

    location = item.get('location') or {}
    lat = item.get('latitude') if item.get('latitude') is not None else location.get('lat')
    lng = item.get('longitude') if item.get('longitude') is not None else location.get('lng')

    try:
        if lat is not None:
            lat = float(lat)
    except (ValueError, TypeError):
        lat = None
    try:
        if lng is not None:
            lng = float(lng)
    except (ValueError, TypeError):
        lng = None

    place_id = item.get('placeId') or item.get('place_id') or ''
    if not place_id and item.get('url'):
        place_id = _extract_place_id_from_url(item['url'])
    if not place_id and title:
        place_id = f"gmaps_{abs(hash(title + raw_address))}"

    website = item.get('website') or item.get('website_url') or None
    url = item.get('url') or item.get('maps_url') or item.get('google_maps_url')
    if not url and place_id and place_id.startswith("ChIJ"):
        url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    elif not url and title:
        url = f"https://www.google.com/maps/search/{urllib.parse.quote(title)}"

    return {
        'platform': 'google_maps',
        'place_id': place_id,
        'title': title,
        'category_name': category_name,
        'category': category,
        'address': address_data.get('address_full') or raw_address,
        'district_area': address_data.get('district_area', ''),
        'city': city,
        'phone_number': raw_phone if raw_phone else None,
        'whatsapp_number': whatsapp,
        'latitude': lat,
        'longitude': lng,
        'reviews_count': reviews_count,
        'total_score': total_score,
        'website': website,
        'url': url,
        'reviews': raw_reviews,
        'packaging_pain_points': pain_points,
        'estimated_commercials': estimated_commercials
    }


def scrape_google_maps_playwright(query: str, city: str = "Makassar", limit: int = 20) -> list[dict]:
    from playwright.sync_api import sync_playwright

    results = []
    search_query = f"{query} {city}"

    with sync_playwright() as p:
        browser = _get_browser(p)
        context = browser.new_context(
            locale="id-ID",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        url = f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}?hl=id"
        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)

        try:
            consent = page.locator('button:has-text("Setuju semua"), button:has-text("Accept all")').first
            if consent.count() > 0:
                consent.click(timeout=2000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        collected = []
        seen_hrefs = set()

        for _ in range(10):
            links = page.locator('a.hfpxzc').all()
            for link in links:
                href = link.get_attribute('href') or ''
                aria_label = link.get_attribute('aria-label') or ''
                if not href or href in seen_hrefs:
                    continue
                if not aria_label:
                    continue
                seen_hrefs.add(href)
                collected.append({
                    'title': aria_label.strip(),
                    'url': href,
                    'place_id': _extract_place_id_from_url(href)
                })
                if len(collected) >= limit * 2:
                    break
            if len(collected) >= limit * 2:
                break
            try:
                feed = page.locator('div[role="feed"]').first
                if feed.count() > 0:
                    feed.evaluate("el => el.scrollBy(0, 2000)")
                    page.wait_for_timeout(1500)
                else:
                    break
            except Exception:
                break

        for entry in collected[:limit]:
            place_id = entry.get('place_id') or ""
            item = {
                'title': entry['title'],
                'url': entry['url'],
                'placeId': place_id,
                'city': city,
            }

            try:
                detail_page = context.new_page()
                detail_page.goto(entry['url'], timeout=45000)
                detail_page.wait_for_timeout(2500)

                addr_btn = detail_page.locator('button[data-item-id="address"]').first
                if addr_btn.count() > 0:
                    addr_aria = addr_btn.get_attribute('aria-label') or ''
                    if addr_aria:
                        item['address'] = addr_aria.replace('Alamat:', '').strip()

                phone_btn = detail_page.locator('button[data-item-id*="phone:"]').first
                if phone_btn.count() > 0:
                    phone_aria = phone_btn.get_attribute('aria-label') or ''
                    if phone_aria:
                        item['phone'] = phone_aria.replace('Telepon:', '').strip()

                web_btn = detail_page.locator('a[data-item-id="authority"]').first
                if web_btn.count() > 0:
                    href_web = web_btn.get_attribute('href')
                    if href_web and not href_web.startswith('https://www.google.com/maps'):
                        item['website'] = href_web

                category_el = detail_page.locator('button[jsaction*="category"] span, span.fontBodyMedium').first
                if category_el.count() > 0:
                    txt = category_el.text_content() or ''
                    if txt and len(txt) < 60:
                        item['categoryName'] = txt.strip()

                rating_el = detail_page.locator('div.F7nice span[aria-hidden="true"]').first
                if rating_el.count() > 0:
                    txt = rating_el.text_content() or ''
                    try:
                        txt_clean = txt.replace(',', '.')
                        if txt_clean:
                            item['totalScore'] = float(re.findall(r'[\d\.]+', txt_clean)[0])
                    except Exception:
                        pass

                reviews_el = detail_page.locator('div.F7nice span[aria-label*="ulasan"], div.F7nice span[aria-label*="review"]').first
                if reviews_el.count() > 0:
                    aria = reviews_el.get_attribute('aria-label') or ''
                    m = re.findall(r'(\d+)', aria)
                    if m:
                        item['reviewsCount'] = int(m[0])

                reviews_list = []
                try:
                    reviews_tab = detail_page.locator('button[role="tab"]:has-text("Ulasan"), button[role="tab"]:has-text("Reviews")').first
                    if reviews_tab.count() > 0:
                        reviews_tab.click(timeout=3000)
                        detail_page.wait_for_timeout(2000)
                except Exception:
                    pass

                try:
                    review_cards = detail_page.locator('div.jftiEf, div[data-review-id]').all()
                    for card in review_cards[:15]:
                        review = {}
                        star_el = card.locator('span.kvMYJc').first
                        if star_el.count() > 0:
                            star_aria = star_el.get_attribute('aria-label') or ''
                            m = re.findall(r'(\d+)', star_aria)
                            if m:
                                review['stars'] = int(m[0])
                        text_el = card.locator('span.wiI7pd').first
                        if text_el.count() > 0:
                            review['text'] = text_el.text_content() or ''
                        date_el = card.locator('span.rsqaWe').first
                        if date_el.count() > 0:
                            review['date'] = date_el.text_content() or ''
                        if review.get('text'):
                            reviews_list.append(review)
                except Exception:
                    pass

                if reviews_list:
                    item['reviews'] = reviews_list

                detail_page.close()
            except Exception:
                try:
                    detail_page.close()
                except Exception:
                    pass

            results.append(parse_place_entry(item, default_city=city))
            if len(results) >= limit:
                break

        browser.close()
    return results


def search_places(query: str, city: str = "Makassar", limit: int = 20, dry_run: bool = False) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would search Google Maps for '{query}' in {city}, limit {limit}")
        return []

    try:
        places = scrape_google_maps_playwright(query, city, limit)
        print(f"Found {len(places)} places")
        return places
    except Exception as e:
        print(f"Error during Playwright scraping: {e}")
        return []


def scrape_negative_reviews(place_id: str, max_stars: int = 3, dry_run: bool = False) -> list[dict]:
    if dry_run:
        print(f"[DRY RUN] Would scrape negative reviews (<=stars) for place_id {place_id}")
        return []

    try:
        from playwright.sync_api import sync_playwright
        results = []
        with sync_playwright() as p:
            browser = _get_browser(p)
            context = browser.new_context(locale="id-ID")
            page = context.new_page()
            url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            page.goto(url, timeout=45000)
            page.wait_for_timeout(3000)

            try:
                reviews_tab = page.locator('button[role="tab"]:has-text("Ulasan"), button[role="tab"]:has-text("Reviews")').first
                if reviews_tab.count() > 0:
                    reviews_tab.click(timeout=3000)
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            review_cards = page.locator('div.jftiEf, div[data-review-id]').all()
            for card in review_cards[:50]:
                review = {}
                star_el = card.locator('span.kvMYJc').first
                if star_el.count() > 0:
                    star_aria = star_el.get_attribute('aria-label') or ''
                    m = re.findall(r'(\d+)', star_aria)
                    if m:
                        stars = int(m[0])
                        review['stars'] = stars
                        if stars > max_stars:
                            continue
                text_el = card.locator('span.wiI7pd').first
                if text_el.count() > 0:
                    review['text'] = text_el.text_content() or ''
                date_el = card.locator('span.rsqaWe').first
                if date_el.count() > 0:
                    review['date'] = date_el.text_content() or ''
                if review.get('text'):
                    results.append(review)

            browser.close()
        print(f"Found {len(results)} negative reviews")
        return results
    except Exception as e:
        print(f"Error during review scraping: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='Google Maps Scraper Module')
    parser.add_argument('--query', type=str, help='Search query')
    parser.add_argument('--city', type=str, default='Makassar', help='City name')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--mode', choices=['search'], default='search')

    args = parser.parse_args()

    output_dir = PROJECT_ROOT / 'data' / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.query:
        print("Error: --query required")
        return

    places = search_places(args.query, args.city, args.limit, args.dry_run)

    if not args.dry_run:
        output_file = output_dir / f'gmaps_{args.city}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(places, f, indent=2, ensure_ascii=False)
        print(f"Saved to {output_file}")
    else:
        if places:
            print(f"Would save {len(places)} places")


if __name__ == '__main__':
    main()
