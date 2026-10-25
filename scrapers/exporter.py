import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv
import json
from datetime import datetime
from typing import Optional

from scrapers.lead_scoring import classify_category
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
    if not category:
        bio = ent.get('biography') or _first_from_records(records, lambda r: r.get('biography') or r.get('bio')) or ''
        category = classify_category(ent.get('business_name') or '', bio, [])
        ent['category'] = category
    category = category or ''

    district = ent.get('district_area') or _first_from_records(
        records, lambda r: r.get('district_area') or r.get('district')) or ''

    address = ent.get('address_full') or _first_from_records(
        records, lambda r: r.get('address_full') or r.get('address')) or ''

    wa = ent.get('whatsapp_number') or ''
    pitch = ent.get('whatsapp_pitch') or generate_whatsapp_pitch(ent)
    wa_link = generate_whatsapp_click_url(wa, pitch) if wa else ''
    products = ent.get('recommended_products') or recommended_products(ent)

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
        'sales_status': 'Belum Dihubungi',
        'sales_notes': '',
    }


def _lead_score_value(ent: dict) -> float:
    try:
        return float(ent.get('lead_score') or 0)
    except (TypeError, ValueError):
        return 0.0

def export_dossiers_to_csv(dossiers: list, output_path: Path, require_whatsapp: bool = True) -> int:
    paired = [(e, build_row(e)) for e in dossiers]
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
