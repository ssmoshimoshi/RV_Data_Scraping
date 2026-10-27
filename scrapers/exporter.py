import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv
from datetime import datetime
from typing import Optional

from scrapers.lead_scoring import classify_category, is_non_commercial, calculate_4_pillars_score, assign_tier
from scrapers.outreach_generator import generate_whatsapp_pitch, generate_whatsapp_click_url, recommended_products
from scrapers.route_cluster import assign_sales_cluster

DEFAULT_PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'

CSV_COLUMNS = [
    'entity_id',
    'business_name',
    'category',
    'district_area',
    'sales_cluster',
    'address_full',
    'whatsapp_number',
    'wa_link_direct',
    'recommended_products',
    'whatsapp_pitch',
    'tier',
    'sales_status',
    'sales_notes',
]

CSV_COLUMNS_FULL = [
    'entity_id',
    'business_name',
    'target_sector',
    'primary_service_pillar',
    'category_raw',
    'priority_tier',
    'lead_score',
    'score_legitimacy',
    'score_velocity',
    'score_turnover',
    'score_budget',
    'detected_service_needs',
    'service_pain_points',
    'est_order_value_idr',
    'recommended_products',
    'address_full',
    'district_area',
    'sales_cluster',
    'latitude',
    'longitude',
    'place_id',
    'gmaps_rating',
    'gmaps_reviews_count',
    'review_samples',
    'website_url',
    'instagram_handle',
    'whatsapp_number',
    'is_wa_valid',
    'has_meta_ads',
    'whatsapp_pitch',
    'sales_status',
    'sales_notes',
]


def find_latest_dossier(processed_dir=DEFAULT_PROCESSED_DIR) -> Optional[Path]:
    files = sorted(Path(processed_dir).glob('unified_dossiers_*.json'), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def _first_from_records(records: list, getter):
    for rec in records:
        if isinstance(rec, dict):
            value = getter(rec)
            if value:
                return value
    return None


def build_row(ent: dict) -> dict:
    records = ent.get('records') or []
    category = ent.get('category') or _first_from_records(
        records, lambda r: r.get('category') or r.get('classified_category'))
    
    # Reklasifikasi jika kategori kosong atau sebelumnya general_commercial
    if not category or category == 'general_commercial':
        bio = ent.get('biography') or _first_from_records(records, lambda r: r.get('biography') or r.get('bio')) or ''
        raw_cat = _first_from_records(records, lambda r: r.get('category_name') or r.get('category_raw')) or ''
        reclassified = classify_category(ent.get('business_name') or '', f"{bio} {raw_cat}", [])
        if reclassified != 'general_commercial' or not category:
            category = reclassified
            ent['category'] = category
    category = category or ''

    district = ent.get('district_area') or _first_from_records(
        records, lambda r: r.get('district_area') or r.get('district')) or ''

    address = ent.get('address_full') or _first_from_records(
        records, lambda r: r.get('address_full') or r.get('address')) or ''

    wa = ent.get('whatsapp_number') or ''
    pitch = generate_whatsapp_pitch(ent)
    wa_link = generate_whatsapp_click_url(wa, pitch) if wa else ''
    products = recommended_products(ent)
    pillars = calculate_4_pillars_score(ent)
    tier = pillars.get('tier', 'Tier D')

    return {
        'entity_id': ent.get('entity_id', ''),
        'business_name': ent.get('business_name', ''),
        'category': category,
        'district_area': district,
        'sales_cluster': assign_sales_cluster(address, district),
        'address_full': address,
        'whatsapp_number': wa,
        'wa_link_direct': wa_link,
        'recommended_products': products,
        'whatsapp_pitch': pitch,
        'tier': tier,
        'sales_status': 'Belum Dihubungi',
        'sales_notes': '',
    }


def _lead_score_value(ent: dict) -> float:
    try:
        return float(ent.get('lead_score') or 0)
    except (TypeError, ValueError):
        return 0.0

def export_dossiers_to_csv(dossiers: list, output_path: Path, require_whatsapp: bool = True) -> int:
    # Filter entitas non-komersial (instansi publik, kelurahan, dinas, dll.)
    commercial_dossiers = [
        e for e in dossiers 
        if not is_non_commercial(e.get('business_name', ''), e.get('biography', ''))
    ]

    paired = [(e, build_row(e)) for e in commercial_dossiers]
    paired.sort(key=lambda p: (p[1].get('sales_cluster', ''), -_lead_score_value(p[0])))
    rows = [row for _, row in paired]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if require_whatsapp:
        main_rows = [r for r in rows if r.get('whatsapp_number')]
        secondary_rows = [r for r in rows if not r.get('whatsapp_number')]
        if secondary_rows:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            secondary_path = output_path.parent / f"dossiers_perlu_riset_{timestamp}.csv"
            with secondary_path.open('w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(secondary_rows)
    else:
        main_rows = rows

    with output_path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(main_rows)
    return len(main_rows)


def build_row_full(ent: dict) -> dict:
    records = ent.get('records') or []
    category = ent.get('category') or _first_from_records(
        records, lambda r: r.get('category') or r.get('classified_category')) or ''
    
    if not category or category == 'general_commercial':
        bio = ent.get('biography') or _first_from_records(records, lambda r: r.get('biography') or r.get('bio')) or ''
        raw_cat = _first_from_records(records, lambda r: r.get('category_name') or r.get('category_raw')) or ''
        reclassified = classify_category(ent.get('business_name') or '', f"{bio} {raw_cat}", [])
        if reclassified != 'general_commercial' or not category:
            category = reclassified

    district = ent.get('district_area') or _first_from_records(
        records, lambda r: r.get('district_area') or r.get('district')) or ''
    address = ent.get('address_full') or _first_from_records(
        records, lambda r: r.get('address_full') or r.get('address')) or ''

    from scrapers.lead_scoring import calculate_4_pillars_score, assign_tier
    wa = ent.get('whatsapp_number') or ''
    pitch = generate_whatsapp_pitch(ent)
    products = recommended_products(ent)
    pillars = calculate_4_pillars_score(ent)
    
    review_snippets = ent.get('review_snippets_json') or _first_from_records(records, lambda r: r.get('review_snippets_json')) or []
    review_samples = ', '.join(review_snippets[:2]) if isinstance(review_snippets, list) else str(review_snippets)[:100]
    
    detected_needs = ent.get('detected_service_needs') or ''
    pain_points = ent.get('service_pain_points') or ''
    if isinstance(detected_needs, list):
        detected_needs = ', '.join(detected_needs)
    if isinstance(pain_points, list):
        pain_points = ', '.join(pain_points)

    return {
        'entity_id': ent.get('entity_id', ''),
        'business_name': ent.get('business_name', ''),
        'target_sector': ent.get('target_sector', ''),
        'primary_service_pillar': ent.get('primary_service_pillar', ''),
        'category_raw': category,
        'priority_tier': ent.get('priority_tier') or pillars.get('tier', 'Tier D'),
        'lead_score': ent.get('lead_score') if ent.get('lead_score') is not None else pillars.get('score_total', 0),
        'score_legitimacy': ent.get('score_legitimacy') if ent.get('score_legitimacy') is not None else pillars.get('score_legitimacy', 0),
        'score_velocity': ent.get('score_velocity') if ent.get('score_velocity') is not None else pillars.get('score_velocity', 0),
        'score_turnover': ent.get('score_turnover') if ent.get('score_turnover') is not None else pillars.get('score_turnover', 0),
        'score_budget': ent.get('score_budget') if ent.get('score_budget') is not None else pillars.get('score_budget', 0),
        'detected_service_needs': detected_needs,
        'service_pain_points': pain_points,
        'est_order_value_idr': ent.get('est_order_value_idr', 0),
        'recommended_products': products,
        'address_full': address,
        'district_area': district,
        'sales_cluster': assign_sales_cluster(address, district),
        'latitude': ent.get('latitude') or _first_from_records(records, lambda r: r.get('latitude')) or '',
        'longitude': ent.get('longitude') or _first_from_records(records, lambda r: r.get('longitude')) or '',
        'place_id': ent.get('place_id') or _first_from_records(records, lambda r: r.get('place_id')) or '',
        'gmaps_rating': ent.get('gmaps_rating') or _first_from_records(records, lambda r: r.get('gmaps_rating')) or '',
        'gmaps_reviews_count': ent.get('gmaps_reviews_count') or _first_from_records(records, lambda r: r.get('gmaps_reviews_count')) or 0,
        'review_samples': review_samples,
        'website_url': ent.get('website_url') or _first_from_records(records, lambda r: r.get('website_url')) or '',
        'instagram_handle': ent.get('instagram_handle') or _first_from_records(records, lambda r: r.get('instagram_handle')) or '',
        'whatsapp_number': wa,
        'is_wa_valid': 1 if wa else 0,
        'has_meta_ads': 1 if ent.get('has_meta_ads') else 0,
        'whatsapp_pitch': pitch,
        'sales_status': ent.get('outreach_status') or ent.get('sales_status') or 'Belum Dihubungi',
        'sales_notes': ent.get('sales_notes') or ent.get('outreach_notes') or '',
    }


def export_full_dossiers_to_csv(dossiers: list, output_path: Path) -> int:
    commercial_dossiers = [
        e for e in dossiers
        if not is_non_commercial(e.get('business_name', ''), e.get('biography', ''))
    ]

    paired = [(e, build_row_full(e)) for e in commercial_dossiers]
    paired.sort(key=lambda p: (p[1].get('sales_cluster', ''), -float(p[1].get('lead_score', 0) or 0)))
    rows = [row for _, row in paired]
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS_FULL)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
