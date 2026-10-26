import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from scrapers.normalizer import normalize_whatsapp, extract_whatsapp_from_url

load_dotenv()

DISTRICTS = {
    'Panakkukang': ['Boulevard Makassar', 'Pengayoman Makassar', 'Panakkukang Makassar'],
    'Rappocini': ['Hertasning Makassar', 'Emmy Saelan Makassar', 'Rappocini Makassar'],
    'Tamalanrea': ['Perintis Kemerdekaan Makassar', 'Tamalanrea Makassar', 'Unhas Makassar'],
    'Ujung Pandang': ['Ujung Pandang Makassar', 'Somba Opu Makassar'],
    'Mariso': ['Mariso Makassar'],
    'Biringkanaya': ['Biringkanaya Makassar'],
}

SECTOR_QUERIES = {
    'fnb_hospitality': [
        'cafe coffee', 'restoran rumah makan', 'katering', 'ayam geprek', 'bakso mie',
        'kopi kafe', 'kedai minuman', 'bakery kue roti',
    ],
    'retail_apparel': [
        'butik pakaian', 'toko baju fashion', 'hijab store', 'distro clothing',
        'toko baju pria wanita', 'butik hijab muslim',
    ],
    'education': [
        'sekolah swasta', 'madrasah aliyah tsanawiyah', 'pondok pesantren', 'bimbel les privat',
        'taman kanak-kanak paud', 'sd smp sma swasta',
    ],
    'corporate_legal': [
        'kantor notaris ppat', 'kantor hukum advokat pengacara', 'klinik kecantikan estetika',
        'konsultan bisnis hukum', 'kantor advokat legal',
    ],
    'event_community': [
        'event organizer wedding', 'dekorasi pameran acara', 'wedding organizer decoration',
        'event planner organizer', 'studio dekorasi pesta',
    ],
    'beauty_skincare': [
        'klinik kecantikan estetik', 'skincare salon spa', 'kecantikan klinik dermato',
    ],
}


def build_queries(sector: str) -> list[tuple[str, str, str]]:
    sectors = list(SECTOR_QUERIES.keys()) if sector == 'all' else [sector]
    queries = []
    for sec in sectors:
        for keyword in SECTOR_QUERIES.get(sec, []):
            for district, areas in DISTRICTS.items():
                for area in areas:
                    queries.append((sec, district, f"{keyword} {area}"))
    return queries


def _load_seen_ids(raw_dir: Path) -> set:
    seen = set()
    for f in raw_dir.glob('harvest_makassar_*.json'):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            if isinstance(data, list):
                seen.update(d.get('place_id') for d in data if d.get('place_id'))
        except (json.JSONDecodeError, OSError):
            pass
    return seen


def _extract_dataset_id(run) -> str:
    if run is None:
        return ""
    if isinstance(run, dict):
        return run.get("defaultDatasetId") or run.get("default_dataset_id", "")
    return getattr(run, "default_dataset_id", "") or getattr(run, "defaultDatasetId", "")


def _run_apify_queries(queries: list[str], limit: int) -> list[dict]:
    from apify_client import ApifyClient
    token = os.getenv('APIFY_API_TOKEN')
    if not token:
        raise RuntimeError('APIFY_API_TOKEN belum dikonfigurasi di .env')
    client = ApifyClient(token)
    run = client.actor('compass/crawler-google-places').call(run_input={
        'searchStringsArray': queries,
        'maxCrawledPlacesPerSearch': limit,
        'language': 'id',
    })
    dataset_id = _extract_dataset_id(run)
    if not dataset_id:
        return []
    return [
        item for item in client.dataset(dataset_id).iterate_items()
        if isinstance(item, dict)
    ]


def _run_harvest_queries(queries: list[str], limit: int) -> list[dict]:
    token = os.getenv('APIFY_API_TOKEN')
    if token:
        try:
            return _run_apify_queries(queries, limit)
        except Exception as e:
            print(f"Peringatan: Panggilan Apify gagal ({e}), beralih ke perayap Playwright lokal...")
    
    from scrapers.gmaps_scraper import search_places
    all_places = []
    for q in queries:
        places = search_places(q, city='Makassar', limit=limit, dry_run=False)
        all_places.extend(places)
    return all_places


def _run_apify_query(query: str, limit: int) -> list[dict]:
    return _run_harvest_queries([query], limit)


def harvest(sector: str = 'all', limit_per_query: int = 10, dry_run: bool = False) -> list[dict]:
    raw_dir = PROJECT_ROOT / 'data' / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)

    queries = build_queries(sector)
    print(f"Sektor: {sector} | Total kombinasi query: {len(queries)} | Limit per query: {limit_per_query}")

    if dry_run:
        print("Mode dry-run: tidak ada panggilan Apify. Contoh query yang akan dijalankan:")
        for sec, district, q in queries[:5]:
            print(f"  [{sec}] {district}: {q}")
        if len(queries) > 5:
            print(f"  ... dan {len(queries) - 5} query lainnya.")
        return []

    seen_ids = _load_seen_ids(raw_dir)
    all_results = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    query_map = {q: (sec, dist) for sec, dist, q in queries}

    chunk_size = 5
    for i in range(0, len(queries), chunk_size):
        chunk = queries[i:i + chunk_size]
        query_strings = [q[2] for q in chunk]
        print(f"Memproses batch {i // chunk_size + 1}/{(len(queries) + chunk_size - 1) // chunk_size} ({len(chunk)} query)...")
        for _, _, q_str in chunk:
            print(f"  - {q_str}")

        try:
            items = _run_harvest_queries(query_strings, limit_per_query)
        except Exception as e:
            print(f"Gagal batch query: {e}")
            continue

        new_items = []
        for item in items:
            pid = item.get('placeId') or item.get('place_id') or ''
            phone_raw = item.get('phone', '') or ''
            website_raw = item.get('website', '') or ''
            wa_num = normalize_whatsapp(phone_raw) or extract_whatsapp_from_url(website_raw) or ''
            search_str = item.get('searchString') or ''
            sec_mapped, dist_mapped = query_map.get(search_str, (chunk[0][0], chunk[0][1]))

            normalized = {
                'place_id': pid,
                'business_name': item.get('title') or item.get('name', ''),
                'address_full': item.get('address', ''),
                'district_area': dist_mapped,
                'city': 'makassar',
                'sector': sec_mapped,
                'category_raw': item.get('categoryName') or item.get('category_name', ''),
                'phone': phone_raw,
                'phone_number': phone_raw,
                'whatsapp_number': wa_num,
                'website': website_raw,
                'reviews_count': item.get('reviewsCount') or item.get('reviews_count', 0),
                'rating': item.get('totalScore') or item.get('rating'),
                'latitude': (item.get('location') or {}).get('lat'),
                'longitude': (item.get('location') or {}).get('lng'),
                'platform': 'google_maps',
                'harvested_at': timestamp,
            }
            if pid and pid in seen_ids:
                continue
            if pid:
                seen_ids.add(pid)
            new_items.append(normalized)

        if new_items:
            slug = chunk[0][2].replace(' ', '_')[:30]
            out_path = raw_dir / f"harvest_makassar_{timestamp}_{slug}_{i // chunk_size + 1}.json"
            out_path.write_text(json.dumps(new_items, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"  Disimpan {len(new_items)} tempat baru -> {out_path.name}")
            all_results.extend(new_items)

    print(f"Panen selesai. Total tempat baru: {len(all_results)}")
    return all_results


def main():
    parser = argparse.ArgumentParser(description='Panen massal Google Maps per kecamatan Makassar')
    parser.add_argument('--sector', choices=list(SECTOR_QUERIES.keys()) + ['all'], default='all')
    parser.add_argument('--limit', '--limit-per-query', dest='limit_per_query', type=int, default=10)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    harvest(sector=args.sector, limit_per_query=args.limit_per_query, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
