import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json

KORIDOR_PANAKKUKANG = ['boulevard', 'pengayoman', 'toddopuli', 'hertasning baru', 'masale', 'pandang']
KORIDOR_RAPPOCINI = ['hertasning', 'emmy saelan', 'pettarani', 'rappocini', 'mapala', 'karunrung']
KORIDOR_UJUNG_PANDANG = ['somba opu', 'penghibur', 'botolempangan', 'sawerigading', 'ujung pandang', 'losari']
KORIDOR_TAMALANREA = ['perintis', 'btp', 'tamalanrea', 'daya', 'biringkanaya', 'sudiang', 'unhas']
KORIDOR_MARISO_MAMAJANG = ['cendrawasih', 'veteran', 'ratulangi', 'mariso', 'mamajang', 'kakaktua']

DEFAULT_CLUSTER = 'Makassar Lainnya'

# Urutan penting:
# - 'ujung pandang' harus diperiksa sebelum 'pandang' (Panakkukang)
# - 'hertasning baru' (Panakkukang) harus diperiksa sebelum 'hertasning' (Rappocini)
_KORIDOR = (
    ('Koridor Ujung Pandang', KORIDOR_UJUNG_PANDANG),
    ('Koridor Panakkukang', KORIDOR_PANAKKUKANG),
    ('Koridor Rappocini', KORIDOR_RAPPOCINI),
    ('Koridor Tamalanrea', KORIDOR_TAMALANREA),
    ('Koridor Mariso Mamajang', KORIDOR_MARISO_MAMAJANG),
)

def assign_sales_cluster(address: str, district: str) -> str:
    text = f"{address or ''} {district or ''}".lower()
    for nama, keywords in _KORIDOR:
        if any(k in text for k in keywords):
            return nama
    return DEFAULT_CLUSTER

def main():
    parser = argparse.ArgumentParser(description='RUANG VISUAL Sales Corridor Clustering')
    parser.add_argument('--mode', choices=['cluster'], default='cluster', help='Mode operasi klasterisasi')
    parser.add_argument('--limit', type=int, default=500, help='Jumlah dossier maksimal yang diproses')
    parser.add_argument('--dry-run', action='store_true', help='Tampilkan hasil tanpa menulis ke disk')
    args = parser.parse_args()

    processed_dir = PROJECT_ROOT / 'data' / 'processed'
    files = sorted(processed_dir.glob('unified_dossiers_*.json'))
    if not files:
        print('Tidak ada file unified_dossiers di data/processed.')
        return
    dossiers = json.loads(files[-1].read_text(encoding='utf-8'))[:args.limit]

    for ent in dossiers:
        cluster = assign_sales_cluster(ent.get('address_full', ''), ent.get('district_area', ''))
        print(f"{ent.get('entity_id', '-')}: {ent.get('business_name', '-')} -> {cluster}")

    if args.dry_run:
        print('Mode dry-run aktif: hasil tidak ditulis ke disk.')
        return
    out_path = processed_dir / 'sales_clusters.json'
    out_path.write_text(json.dumps([
        {'entity_id': e.get('entity_id', ''),
         'sales_cluster': assign_sales_cluster(e.get('address_full', ''), e.get('district_area', ''))}
        for e in dossiers
    ], indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Hasil disimpan: {out_path}")

if __name__ == '__main__':
    main()
