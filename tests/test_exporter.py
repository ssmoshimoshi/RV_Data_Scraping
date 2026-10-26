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
from scrapers.exporter import (
    export_dossiers_to_csv,
    export_full_dossiers_to_csv,
    find_latest_dossier,
    CSV_COLUMNS,
    CSV_COLUMNS_FULL,
    build_row,
    build_row_full,
)

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

    def test_csv_has_13_required_columns(self):
        required = {
            'entity_id', 'business_name', 'category', 'district_area', 'sales_cluster',
            'address_full', 'whatsapp_number', 'wa_link_direct',
            'recommended_products', 'whatsapp_pitch', 'tier', 'sales_status', 'sales_notes',
        }
        self.assertEqual(set(CSV_COLUMNS), required)
        self.assertEqual(len(CSV_COLUMNS), 13)

    def test_sales_cluster_positioned_after_district_area(self):
        idx = CSV_COLUMNS.index('sales_cluster')
        self.assertEqual(CSV_COLUMNS[idx - 1], 'district_area')

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

    def test_sales_cluster_assigned_from_address(self):
        ent = {
            'entity_id': 'ent_0005',
            'business_name': 'Warung Coto Daeng',
            'category': 'fnb_food_resto',
            'district_area': 'Panakkukang',
            'address_full': 'Jl. Boulevard No. 10 Makassar',
            'records': [],
        }
        row = build_row(ent)
        self.assertEqual(row['sales_cluster'], 'Koridor Panakkukang')

    def test_sales_cluster_assigned_from_district_only(self):
        ent = {
            'entity_id': 'ent_0006',
            'business_name': 'Squid Coffee',
            'category': 'fnb_beverage',
            'district_area': 'Tamalanrea',
            'records': [],
        }
        row = build_row(ent)
        self.assertEqual(row['sales_cluster'], 'Koridor Tamalanrea')

    def test_sales_cluster_fallback(self):
        ent = {
            'entity_id': 'ent_0007',
            'business_name': 'Toko Misteri',
            'category': 'fnb_food_resto',
            'address_full': 'Jl. Antah Berantah No. 1',
            'district_area': 'Entah',
            'records': [],
        }
        row = build_row(ent)
        self.assertEqual(row['sales_cluster'], 'Makassar Lainnya')


class TestExportSorting(unittest.TestCase):

    def test_rows_sorted_by_cluster_then_score_desc(self):
        dossiers = [
            {
                'entity_id': 'e1', 'business_name': 'A', 'category': 'fnb_food_resto',
                'district_area': 'Tamalanrea', 'address_full': 'Jl. Perintis Km. 8',
                'whatsapp_number': '628111111111', 'lead_score': 70, 'records': [],
            },
            {
                'entity_id': 'e2', 'business_name': 'B', 'category': 'fnb_beverage',
                'district_area': 'Panakkukang', 'address_full': 'Jl. Boulevard No. 2',
                'whatsapp_number': '628222222222', 'lead_score': 60, 'records': [],
            },
            {
                'entity_id': 'e3', 'business_name': 'C', 'category': 'fnb_bakery',
                'district_area': 'Panakkukang', 'address_full': 'Jl. Pengayoman No. 9',
                'whatsapp_number': '628333333333', 'lead_score': 90, 'records': [],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            export_dossiers_to_csv(dossiers, out, require_whatsapp=False)
            with out.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual([r['entity_id'] for r in rows], ['e3', 'e2', 'e1'])
            self.assertEqual(rows[0]['sales_cluster'], 'Koridor Panakkukang')
            self.assertEqual(rows[2]['sales_cluster'], 'Koridor Tamalanrea')

    def test_sort_tolerates_missing_lead_score(self):
        dossiers = [
            {'entity_id': 'e1', 'business_name': 'A', 'address_full': 'Jl. Boulevard', 'records': []},
            {'entity_id': 'e2', 'business_name': 'B', 'address_full': 'Jl. Boulevard No. 3', 'lead_score': 'invalid', 'records': []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.csv'
            count = export_dossiers_to_csv(dossiers, out, require_whatsapp=False)
            self.assertEqual(count, 2)


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


class TestExportFullCSV(unittest.TestCase):

    def test_csv_full_has_32_columns(self):
        self.assertEqual(len(CSV_COLUMNS_FULL), 32)
        expected_keys = {
            'entity_id', 'business_name', 'target_sector', 'primary_service_pillar',
            'category_raw', 'priority_tier', 'lead_score', 'score_legitimacy',
            'score_velocity', 'score_turnover', 'score_budget', 'detected_service_needs',
            'service_pain_points', 'est_order_value_idr', 'recommended_products',
            'address_full', 'district_area', 'sales_cluster', 'latitude', 'longitude',
            'place_id', 'gmaps_rating', 'gmaps_reviews_count', 'review_samples',
            'website_url', 'instagram_handle', 'whatsapp_number', 'is_wa_valid',
            'has_meta_ads', 'whatsapp_pitch', 'sales_status', 'sales_notes',
        }
        self.assertEqual(set(CSV_COLUMNS_FULL), expected_keys)

    def test_build_row_full_calculates_scores_accurately(self):
        dossier = {
            'entity_id': 'ent_test_full',
            'business_name': 'Kopi Sejahtera Makassar',
            'category': 'fnb_hospitality',
            'target_sector': 'fnb_hospitality',
            'primary_service_pillar': 'label_sticker',
            'address_full': 'Jl. Pengayoman No. 12',
            'district_area': 'Panakkukang',
            'google_maps_place_id': 'place_kopi_123',
            'rating': 4.7,
            'whatsapp_number': '6281234567890',
            'latest_post_date': '2026-10-25T12:00:00',
            'is_ad_active': True,
            'outreach_status': 'Tertarik',
            'sales_notes': 'Sampel cup sudah dikirimkan.',
        }
        row = build_row_full(dossier)
        self.assertGreaterEqual(row['lead_score'], 80)
        self.assertEqual(row['score_legitimacy'], 25)
        self.assertEqual(row['score_turnover'], 30)
        self.assertEqual(row['score_budget'], 20)
        self.assertEqual(row['priority_tier'], 'Tier A')
        self.assertEqual(row['sales_status'], 'Tertarik')
        self.assertEqual(row['sales_notes'], 'Sampel cup sudah dikirimkan.')

    def test_export_full_writes_correct_csv(self):
        dossiers = [
            {
                'entity_id': 'ent_101',
                'business_name': 'SMA Unggulan Harapan',
                'category': 'education',
                'target_sector': 'education',
                'primary_service_pillar': 'office_school',
                'address_full': 'Jl. Perintis Kemerdekaan KM 10',
                'district_area': 'Tamalanrea',
                'place_id': 'place_sma_101',
                'gmaps_rating': 4.8,
                'whatsapp_number': '628114455667',
                'records': [],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_csv = Path(tmp) / 'full_export.csv'
            count = export_full_dossiers_to_csv(dossiers, out_csv)
            self.assertEqual(count, 1)

            with out_csv.open(encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['entity_id'], 'ent_101')
                self.assertGreater(int(rows[0]['lead_score']), 0)
                self.assertGreater(int(rows[0]['score_turnover']), 0)


if __name__ == '__main__':
    unittest.main()
