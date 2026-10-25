import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import math
from datetime import datetime
from difflib import SequenceMatcher

from scrapers.normalizer import normalize_whatsapp, extract_whatsapp_from_url
from scrapers.biolink_resolver import is_biolink_url, resolve_biolink_whatsapp

# Referensi: PRD_RUANG_VISUAL_MARKET_INTELLIGENCE.md Bab 5.6
SIMILARITY_THRESHOLD = 0.85
GEO_MATCH_METERS = 150.0


def _jaro(s1: str, s2: str) -> float:
    len1, len2 = len(s1), len(s2)
    window = max(0, max(len1, len2) // 2 - 1)
    flags1 = [False] * len1
    flags2 = [False] * len2
    matches = 0
    for i in range(len1):
        lo, hi = max(0, i - window), min(i + window + 1, len2)
        for j in range(lo, hi):
            if not flags2[j] and s1[i] == s2[j]:
                flags1[i] = flags2[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    transpositions = 0
    k = 0
    for i in range(len1):
        if flags1[i]:
            while not flags2[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
    transpositions //= 2
    return (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3


def jaro_winkler(s1: str, s2: str) -> float:
    # jellyfish ada di requirements.txt tetapi belum terpasang; implementasi stdlib agar modul jalan di interpreter mana pun
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    jaro = _jaro(s1, s2)
    prefix = 0
    for a, b in zip(s1[:4], s2[:4]):
        if a != b:
            break
        prefix += 1
    return jaro + prefix * 0.1 * (1 - jaro)


def token_sort_ratio(s1: str, s2: str) -> float:
    a = ' '.join(sorted(s1.lower().split()))
    b = ' '.join(sorted(s2.lower().split()))
    return SequenceMatcher(None, a, b).ratio()


def name_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return max(jaro_winkler(a.lower(), b.lower()), token_sort_ratio(a, b))


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * radius * math.asin(math.sqrt(a))


def extract_fields(record: dict) -> dict:
    name = ''
    for key in ('business_name', 'title', 'display_name', 'merchant_name', 'brand_name'):
        if record.get(key):
            name = record[key]
            break
    raw_phone = record.get('whatsapp_number') or record.get('phone_number') or record.get('phone') or ''
    wa = normalize_whatsapp(raw_phone)
    if not wa and record.get('website'):
        wa = extract_whatsapp_from_url(record['website'])
    if not wa and is_biolink_url(record.get('website') or ''):
        wa = resolve_biolink_whatsapp(record['website'])
    return {
        'name': name,
        'platform': record.get('platform', ''),
        'whatsapp': wa,
        'city': (record.get('city') or '').strip().lower(),
        'district': (record.get('district_area') or '').strip().lower(),
        'lat': record.get('latitude'),
        'lon': record.get('longitude'),
    }


def _merge_check(fa: dict, fb: dict):
    if fa['whatsapp'] and fa['whatsapp'] == fb['whatsapp']:
        return 'whatsapp_exact'
    if name_similarity(fa['name'], fb['name']) < SIMILARITY_THRESHOLD:
        return None
    if (fa['city'] and fa['city'] == fb['city']) or (fa['district'] and fa['district'] == fb['district']):
        return 'name_fuzzy'
    if None not in (fa['lat'], fa['lon'], fb['lat'], fb['lon']) \
            and haversine_m(fa['lat'], fa['lon'], fb['lat'], fb['lon']) <= GEO_MATCH_METERS:
        return 'geo_150m'
    return None


def match_entities(records: list) -> list:
    entities = []
    for rec in records:
        f = extract_fields(rec)
        target = None
        reason = None
        for ent in entities:
            for member in ent['_fields']:
                reason = _merge_check(f, member)
                if reason:
                    target = ent
                    break
            if target:
                break
        if target is None:
            entities.append({
                'business_name': f['name'],
                'whatsapp_number': f['whatsapp'],
                'platforms': [f['platform']] if f['platform'] else [],
                'city': f['city'],
                'district_area': f['district'],
                'match_reasons': [],
                'records': [rec],
                '_fields': [f],
            })
            continue
        target['records'].append(rec)
        target['_fields'].append(f)
        target['platforms'] = sorted({x['platform'] for x in target['_fields'] if x['platform']})
        if reason not in target['match_reasons']:
            target['match_reasons'].append(reason)
        if not target['whatsapp_number'] and f['whatsapp']:
            target['whatsapp_number'] = f['whatsapp']
        for dst, src in (('city', 'city'), ('district_area', 'district')):
            if not target[dst] and f[src]:
                target[dst] = f[src]
    for i, ent in enumerate(entities, 1):
        ent['entity_id'] = f'ent_{i:04d}'
        ent.pop('_fields')
    return entities


def load_raw_records(raw_dir: Path, limit: int) -> list:
    records = []
    for path in sorted(Path(raw_dir).glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            print(f"Peringatan: file {path.name} tidak dapat dibaca, dilewati.")
            continue
        if isinstance(data, list):
            records.extend(x for x in data if isinstance(x, dict))
        if len(records) >= limit:
            break
    return records[:limit]


def main():
    parser = argparse.ArgumentParser(description='RUANG VISUAL Cross-Platform Entity Matcher (PRD v2.0 Bab 5.6)')
    parser.add_argument('--mode', choices=['match'], default='match', help='Mode operasi matcher')
    parser.add_argument('--limit', type=int, default=500, help='Jumlah record mentah maksimal yang dibaca')
    parser.add_argument('--dry-run', action='store_true', help='Tampilkan hasil tanpa menulis ke disk')
    args = parser.parse_args()

    raw_dir = PROJECT_ROOT / 'data' / 'raw'
    records = load_raw_records(raw_dir, args.limit)
    print(f"Record dibaca dari {raw_dir}: {len(records)}")

    if args.mode == 'match':
        entities = match_entities(records)
        merged = [e for e in entities if len(e['records']) > 1]
        print(f"Entitas unik: {len(entities)} | Entitas gabungan lintas platform: {len(merged)}")
        for ent in merged:
            print(f"  {ent['entity_id']}: {ent['business_name']} | Platform: {', '.join(ent['platforms'])} "
                  f"| WhatsApp: {ent['whatsapp_number'] or '-'} | Alasan: {', '.join(ent['match_reasons'])}")
        if args.dry_run:
            print('Mode dry-run aktif: hasil tidak ditulis ke disk.')
            return
        out_dir = PROJECT_ROOT / 'data' / 'processed'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"matched_entities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        out_path.write_text(json.dumps(entities, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"Hasil disimpan: {out_path}")


if __name__ == '__main__':
    main()
