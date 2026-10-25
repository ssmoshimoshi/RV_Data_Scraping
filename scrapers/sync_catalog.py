import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

APP_ENV_PATH = Path('/Users/muhammadfanani/Documents/2026 COMMISSION/RUANG VISUAL/RUANG VISUAL APP/.env.local')
CATALOG_OUTPUT_DIR = PROJECT_ROOT / 'data' / 'catalog'
CATALOG_OUTPUT_FILE = CATALOG_OUTPUT_DIR / 'ruang_visual_catalog.json'


def _load_app_credentials():
    url = os.getenv('PROD_SUPABASE_URL')
    key = os.getenv('PROD_SUPABASE_ANON_KEY')

    if not url or not key:
        if APP_ENV_PATH.exists():
            try:
                for line in APP_ENV_PATH.read_text(encoding='utf-8').splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('\"\'')
                        if k == 'NEXT_PUBLIC_SUPABASE_URL' and not url:
                            url = v
                        elif k == 'NEXT_PUBLIC_SUPABASE_ANON_KEY' and not key:
                            key = v
            except OSError:
                pass
    return url, key


def sync_catalog(output_file: Path = CATALOG_OUTPUT_FILE) -> dict:
    url, key = _load_app_credentials()
    if not url or not key:
        raise RuntimeError('Kredensial Supabase aplikasi utama (NEXT_PUBLIC_SUPABASE_URL / ANON_KEY) tidak ditemukan.')

    from supabase import create_client
    # Hak akses dibatasi hanya menggunakan ANON KEY (Strictly Read-Only)
    client = create_client(url, key)

    print('Mengambil data katalog produk dari Supabase produksi (Mode: Read-Only)...')

    # 1. Ambil template produk
    res_tpl = client.table('product_templates').select(
        'id, name, category, unit, description, is_active, pricing_tiers'
    ).execute()
    templates = res_tpl.data or []

    # 2. Ambil master items (bahan dan jasa)
    res_items = client.table('master_items').select(
        'id, itemCode, type, subCategory, name, baseUnit'
    ).execute()
    items = res_items.data or []

    catalog_data = {
        'synced_at': datetime.now().isoformat(),
        'source': 'ruang_visual_app_master_items',
        'total_templates': len(templates),
        'total_master_items': len(items),
        'product_templates': templates,
        'master_items': items
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(catalog_data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Katalog berhasil disinkronkan ke snapshot lokal: {output_file}')
    print(f'Total template produk: {len(templates)}, Total master items: {len(items)}')

    return catalog_data


def load_cached_catalog(output_file: Path = CATALOG_OUTPUT_FILE) -> dict:
    if output_file.exists():
        try:
            return json.loads(output_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            pass
    return sync_catalog(output_file)


if __name__ == '__main__':
    sync_catalog()
