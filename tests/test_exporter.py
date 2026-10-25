import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv
import json
import os
import re
import tempfile
import unittest
from scrapers.exporter import export_dossiers_to_csv, find_latest_dossier, CSV_COLUMNS, build_row

EMOJI_PATTERN = re.compile(
    r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2B00-\u2BFF\uFE0F]'
)

SAMPLE_DOSSIERS = [
    {
        'entity_id': 'ent_0001',
        'business_name': 'Warung Coto Daeng',
        'category': 'fnb_food_resto',
        'city': 'Makassar',
        'district_area': 'Panakkukang',
        'address_full': 'Jl. Boulevard No. 10 Makassar',
        'whatsapp_number': '6281234567890',
        'platforms': ['google_maps', 'gofood'],
        'lead_score': 85,
        'priority_tier': 'Tier A',
        'records': [],
    },
    {
        'entity_id': 'ent_0002',
        'business_name': 'Squid Coffee',
        'category': 'fnb_beverage',
        'city': 'Makassar',
        'district_area': 'Tamalanrea',
        'address_full': '',
        'whatsapp_number': '',
        'platforms': ['tiktok'],
        'records': [],
    },
]


class TestCSVColumns(unittest.TestCase):

    def test_csv_has_11_required_columns(self):
        required = {
            'entity_id', 'business_name', 'category', 'district_area',
            'address_full', 'whatsapp_number', 'wa_link_direct',
            'recommended_products', 'whatsapp_pitch', 'sales_status', 'sales_notes',
        }
        self.assertEqual(set(CSV_COLUMNS), required)
        self.assertEqual(len(CSV_COLUMNS), 11)

    def test_export_writes_correct_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            export_dossiers_to_csv(SAMPLE_DOSSIERS, out)
            with out.open(encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.assertEqual(set(reader.fieldnames), set(CSV_COLUMNS))

    def test_export_row_count_matches_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            count = export_dossiers_to_csv(SAMPLE_DOSSIERS, out, require_whatsapp=False)
            self.assertEqual(count, len(SAMPLE_DOSSIERS))

    def test_sales_status_default_belum_dihubungi(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            export_dossiers_to_csv(SAMPLE_DOSSIERS, out)
            with out.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                self.assertEqual(row['sales_status'], 'Belum Dihubungi')

    def test_sales_notes_empty_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            export_dossiers_to_csv(SAMPLE_DOSSIERS, out)
            with out.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                self.assertEqual(row['sales_notes'], '')

    def test_wa_link_direct_present_when_phone_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            export_dossiers_to_csv(SAMPLE_DOSSIERS, out)
            with out.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            row_with_phone = next(r for r in rows if r['whatsapp_number'])
            self.assertTrue(row_with_phone['wa_link_direct'].startswith('https://wa.me/'))

    def test_wa_link_empty_when_no_phone_in_unfiltered_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            export_dossiers_to_csv(SAMPLE_DOSSIERS, out, require_whatsapp=False)
            with out.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            row_no_phone = next(r for r in rows if not r['whatsapp_number'])
            self.assertEqual(row_no_phone['wa_link_direct'], '')

    def test_no_emoji_in_csv_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            export_dossiers_to_csv(SAMPLE_DOSSIERS, out)
            content = out.read_text(encoding='utf-8-sig')
            self.assertIsNone(EMOJI_PATTERN.search(content), "Emoji ditemukan di output CSV")

    def test_recommended_products_not_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            export_dossiers_to_csv(SAMPLE_DOSSIERS, out)
            with out.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                self.assertNotEqual(row['recommended_products'], '')


class TestBuildRow(unittest.TestCase):

    def test_district_area_populated(self):
        ent = {
            'entity_id': 'ent_0003',
            'business_name': 'Kafe Angin',
            'category': 'fnb_beverage',
            'district_area': 'Rappocini',
            'records': [],
        }
        row = build_row(ent)
        self.assertEqual(row['district_area'], 'Rappocini')

    def test_address_full_from_records_fallback(self):
        ent = {
            'entity_id': 'ent_0004',
            'business_name': 'Toko Kain',
            'category': 'fashion_retail',
            'records': [{'address': 'Jl. Hertasning No. 5'}],
        }
        row = build_row(ent)
        self.assertEqual(row['address_full'], 'Jl. Hertasning No. 5')

    def test_tiktok_no_category_gets_classified(self):
        ent = {
            'entity_id': 'ent_9001',
            'business_name': 'Kuliner Makassar Enak',
            'platforms': ['tiktok'],
            'records': [],
        }
        row = build_row(ent)
        self.assertNotEqual(row['category'], '')
        self.assertEqual(row['category'], 'fnb_food_resto')


class TestFindLatestDossier(unittest.TestCase):

    def test_returns_most_recent_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            older = Path(tmp) / 'unified_dossiers_Makassar_20261001_000000.json'
            newer = Path(tmp) / 'unified_dossiers_Makassar_20261025_000000.json'
            other = Path(tmp) / 'matched_entities_20261025.json'
            for p in (older, newer, other):
                p.write_text('[]', encoding='utf-8')
            os.utime(older, (1000000000, 1000000000))
            os.utime(newer, (2000000000, 2000000000))
            self.assertEqual(find_latest_dossier(Path(tmp)), newer)

    def test_returns_none_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_latest_dossier(Path(tmp)))


class TestCategoryFallback(unittest.TestCase):

    def test_hampers_classified_general_commercial(self):
        ent = {
            'entity_id': 'ent_9002',
            'business_name': 'Hampers Custom Jakarta',
            'platforms': ['tiktok'],
            'records': [],
        }
        row = build_row(ent)
        self.assertNotEqual(row['category'], '')
        self.assertEqual(row['category'], 'general_commercial')

    def test_existing_category_not_overwritten(self):
        ent = {
            'entity_id': 'ent_9003',
            'business_name': 'Toko Serba Ada',
            'category': 'fnb_food_resto',
            'records': [],
        }
        row = build_row(ent)
        self.assertEqual(row['category'], 'fnb_food_resto')


class TestWhatsAppFiltering(unittest.TestCase):

    def test_filter_requires_whatsapp_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            count = export_dossiers_to_csv(SAMPLE_DOSSIERS, out)
            self.assertEqual(count, 1)

            with out.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['entity_id'], 'ent_0001')
            self.assertEqual(rows[0]['whatsapp_number'], '6281234567890')

            secondary_files = list(Path(tmp).glob('dossiers_perlu_riset_*.csv'))
            self.assertEqual(len(secondary_files), 1)
            with secondary_files[0].open(encoding='utf-8-sig') as f:
                sec_rows = list(csv.DictReader(f))
            self.assertEqual(len(sec_rows), 1)
            self.assertEqual(sec_rows[0]['entity_id'], 'ent_0002')
            self.assertEqual(sec_rows[0]['whatsapp_number'], '')

    def test_filter_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            count = export_dossiers_to_csv(SAMPLE_DOSSIERS, out, require_whatsapp=False)
            self.assertEqual(count, 2)

            with out.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)

            secondary_files = list(Path(tmp).glob('dossiers_perlu_riset_*.csv'))
            self.assertEqual(len(secondary_files), 0)

    def test_all_have_whatsapp_no_secondary_file_created(self):
        dossiers_all_wa = [
            {'entity_id': 'ent_0001', 'business_name': 'Toko 1', 'whatsapp_number': '62811111111', 'records': []},
            {'entity_id': 'ent_0002', 'business_name': 'Toko 2', 'whatsapp_number': '62822222222', 'records': []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            count = export_dossiers_to_csv(dossiers_all_wa, out, require_whatsapp=True)
            self.assertEqual(count, 2)
            secondary_files = list(Path(tmp).glob('dossiers_perlu_riset_*.csv'))
            self.assertEqual(len(secondary_files), 0)


if __name__ == '__main__':
    unittest.main()
