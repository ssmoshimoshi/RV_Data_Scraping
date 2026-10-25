import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import tempfile
import unittest
from scrapers.entity_matcher import (
    jaro_winkler,
    token_sort_ratio,
    name_similarity,
    haversine_m,
    extract_fields,
    match_entities,
    load_raw_records,
)


class TestJaroWinkler(unittest.TestCase):

    def test_identical_strings(self):
        self.assertAlmostEqual(jaro_winkler('martha', 'martha'), 1.0)

    def test_known_value_martha(self):
        self.assertAlmostEqual(jaro_winkler('martha', 'marhta'), 0.96, places=2)

    def test_empty_string_returns_zero(self):
        self.assertEqual(jaro_winkler('', 'martha'), 0.0)
        self.assertEqual(jaro_winkler('martha', ''), 0.0)

    def test_disjoint_strings(self):
        self.assertAlmostEqual(jaro_winkler('abc', 'xyz'), 0.0)


class TestTokenSortRatio(unittest.TestCase):

    def test_reordered_tokens(self):
        self.assertAlmostEqual(token_sort_ratio('Kopi Susu', 'Susu Kopi'), 1.0)

    def test_different_strings(self):
        self.assertLess(token_sort_ratio('toko bunga', 'bengkel motor'), 0.7)


class TestNameSimilarity(unittest.TestCase):

    def test_case_insensitive(self):
        self.assertAlmostEqual(name_similarity('KOZI Coffee', 'kozi coffee'), 1.0)

    def test_empty_name_returns_zero(self):
        self.assertEqual(name_similarity('', ''), 0.0)
        self.assertEqual(name_similarity('kozi', ''), 0.0)

    def test_suffix_branch_above_threshold(self):
        self.assertGreaterEqual(name_similarity('KOZI Coffee Makassar', 'Kozi Coffee'), 0.85)

    def test_unrelated_names_below_threshold(self):
        self.assertLess(name_similarity('Squid Coffee', 'Bengkel Jaya Motor'), 0.85)


class TestHaversine(unittest.TestCase):

    def test_one_degree_latitude(self):
        self.assertAlmostEqual(haversine_m(0.0, 0.0, 1.0, 0.0), 111195.0, delta=500.0)

    def test_same_point_zero(self):
        self.assertEqual(haversine_m(-5.15, 119.44, -5.15, 119.44), 0.0)


class TestExtractFields(unittest.TestCase):

    def test_gmaps_record(self):
        rec = {
            'platform': 'google_maps',
            'title': 'Squid Coffee',
            'whatsapp_number': '628170772777',
            'city': 'Makassar',
            'district_area': 'Panakkukang',
            'latitude': -5.15,
            'longitude': 119.44,
        }
        f = extract_fields(rec)
        self.assertEqual(f['name'], 'Squid Coffee')
        self.assertEqual(f['whatsapp'], '628170772777')
        self.assertEqual(f['city'], 'makassar')
        self.assertEqual(f['lat'], -5.15)

    def test_food_delivery_phone_alias(self):
        rec = {'platform': 'go_food', 'merchant_name': 'Ayam Geprek', 'phone_number': '081234567890'}
        f = extract_fields(rec)
        self.assertEqual(f['name'], 'Ayam Geprek')
        self.assertEqual(f['whatsapp'], '6281234567890')

    def test_tiktok_display_name_alias(self):
        rec = {'platform': 'tiktok', 'display_name': 'Hampers Custom', 'username': '@hampers'}
        f = extract_fields(rec)
        self.assertEqual(f['name'], 'Hampers Custom')


class TestMatchEntities(unittest.TestCase):

    def test_merge_by_whatsapp_exact(self):
        records = [
            {'platform': 'google_maps', 'title': 'Squid Coffee', 'whatsapp_number': '+62 817-0772-777'},
            {'platform': 'tiktok', 'display_name': 'squid.coffee', 'whatsapp_number': '08170772777'},
        ]
        entities = match_entities(records)
        self.assertEqual(len(entities), 1)
        self.assertEqual(sorted(entities[0]['platforms']), ['google_maps', 'tiktok'])
        self.assertEqual(entities[0]['whatsapp_number'], '628170772777')
        self.assertIn('whatsapp_exact', entities[0]['match_reasons'])

    def test_merge_by_fuzzy_name_same_city(self):
        records = [
            {'platform': 'google_maps', 'title': 'KOZI Coffee Makassar', 'city': 'Makassar'},
            {'platform': 'instagram', 'business_name': 'Kozi Coffee', 'city': 'Makassar'},
        ]
        entities = match_entities(records)
        self.assertEqual(len(entities), 1)
        self.assertIn('name_fuzzy', entities[0]['match_reasons'])

    def test_no_merge_same_name_different_city(self):
        records = [
            {'platform': 'google_maps', 'title': 'KOZI Coffee', 'city': 'Makassar'},
            {'platform': 'instagram', 'business_name': 'KOZI Coffee', 'city': 'Bandung'},
        ]
        entities = match_entities(records)
        self.assertEqual(len(entities), 2)

    def test_merge_by_geo_distance_under_150m(self):
        records = [
            {'platform': 'google_maps', 'title': 'Squid Coffee', 'latitude': -5.15458, 'longitude': 119.44104},
            {'platform': 'go_food', 'merchant_name': 'Squid Coffee', 'latitude': -5.15460, 'longitude': 119.44110},
        ]
        entities = match_entities(records)
        self.assertEqual(len(entities), 1)
        self.assertIn('geo_150m', entities[0]['match_reasons'])

    def test_no_merge_far_coordinates(self):
        records = [
            {'platform': 'google_maps', 'title': 'Squid Coffee', 'latitude': -5.15458, 'longitude': 119.44104},
            {'platform': 'go_food', 'merchant_name': 'Squid Coffee', 'latitude': -5.20000, 'longitude': 119.50000},
        ]
        entities = match_entities(records)
        self.assertEqual(len(entities), 2)

    def test_unrelated_records_stay_separate(self):
        records = [
            {'platform': 'google_maps', 'title': 'Squid Coffee', 'whatsapp_number': '628170772777'},
            {'platform': 'tiktok', 'display_name': 'Bengkel Jaya', 'whatsapp_number': '628567891234'},
        ]
        entities = match_entities(records)
        self.assertEqual(len(entities), 2)

    def test_entity_keeps_source_records(self):
        records = [
            {'platform': 'google_maps', 'title': 'Squid Coffee', 'whatsapp_number': '628170772777'},
            {'platform': 'tiktok', 'display_name': 'squid.coffee', 'whatsapp_number': '628170772777'},
        ]
        entities = match_entities(records)
        self.assertEqual(len(entities[0]['records']), 2)

    def test_empty_input(self):
        self.assertEqual(match_entities([]), [])


class TestLoadRawRecords(unittest.TestCase):

    def test_reads_json_files_with_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'a.json').write_text(json.dumps([
                {'platform': 'tiktok', 'display_name': 'X'},
                {'platform': 'tiktok', 'display_name': 'Y'},
            ]))
            Path(tmp, 'b.json').write_text(json.dumps({'single': {'platform': 'gmaps'}}))
            records = load_raw_records(Path(tmp), limit=10)
            self.assertEqual(len(records), 2)
            limited = load_raw_records(Path(tmp), limit=1)
            self.assertEqual(len(limited), 1)

    def test_invalid_json_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'rusak.json').write_text('bukan json')
            self.assertEqual(load_raw_records(Path(tmp), limit=10), [])


if __name__ == '__main__':
    unittest.main()
