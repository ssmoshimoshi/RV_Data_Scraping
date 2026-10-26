import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import tempfile
import unittest
from unittest.mock import MagicMock
from scrapers.harvest_makassar import build_queries, harvest, DISTRICTS, SECTOR_QUERIES, _extract_dataset_id


class TestBuildQueries(unittest.TestCase):

    def test_fnb_queries_cover_all_districts(self):
        queries = build_queries('fnb_hospitality')
        districts_covered = {q[1] for q in queries}
        self.assertEqual(districts_covered, set(DISTRICTS.keys()))

    def test_all_sector_includes_fnb_fashion_skincare(self):
        queries = build_queries('all')
        sectors_covered = {q[0] for q in queries}
        self.assertEqual(sectors_covered, set(SECTOR_QUERIES.keys()))

    def test_query_string_contains_keyword_and_area(self):
        queries = build_queries('retail_apparel')
        query_strings = [q[2] for q in queries]
        self.assertTrue(any('butik pakaian' in qs for qs in query_strings))
        self.assertTrue(any('Makassar' in qs for qs in query_strings))

    def test_total_count_is_deterministic(self):
        q_fnb = build_queries('fnb_hospitality')
        total_areas = sum(len(areas) for areas in DISTRICTS.values())
        expected = len(SECTOR_QUERIES['fnb_hospitality']) * total_areas
        self.assertEqual(len(q_fnb), expected)

    def test_skincare_queries_present(self):
        queries = build_queries('beauty_skincare')
        query_strings = [q[2] for q in queries]
        self.assertTrue(any('klinik kecantikan' in qs for qs in query_strings))


class TestExtractDatasetId(unittest.TestCase):

    def test_extract_from_dict_camel_case(self):
        run = {'defaultDatasetId': 'dataset_xyz123'}
        self.assertEqual(_extract_dataset_id(run), 'dataset_xyz123')

    def test_extract_from_dict_snake_case(self):
        run = {'default_dataset_id': 'dataset_abc456'}
        self.assertEqual(_extract_dataset_id(run), 'dataset_abc456')

    def test_extract_from_mock_object_camel_case(self):
        run = MagicMock()
        del run.default_dataset_id
        run.defaultDatasetId = 'dataset_obj_camel'
        self.assertEqual(_extract_dataset_id(run), 'dataset_obj_camel')

    def test_extract_from_mock_object_snake_case(self):
        run = MagicMock()
        run.default_dataset_id = 'dataset_obj_snake'
        self.assertEqual(_extract_dataset_id(run), 'dataset_obj_snake')

    def test_extract_from_none(self):
        self.assertEqual(_extract_dataset_id(None), '')

    def test_extract_from_empty_dict(self):
        self.assertEqual(_extract_dataset_id({}), '')


class TestDeduplikasi(unittest.TestCase):

    def test_dry_run_returns_empty_list(self):
        result = harvest(sector='fnb', limit_per_query=5, dry_run=True)
        self.assertEqual(result, [])

    def test_seen_ids_dedup(self):
        from scrapers.harvest_makassar import _load_seen_ids
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            data = [{'place_id': 'ABC123', 'business_name': 'Toko A'}]
            (raw_dir / 'harvest_makassar_20261025_000000_test.json').write_text(
                json.dumps(data), encoding='utf-8'
            )
            seen = _load_seen_ids(raw_dir)
            self.assertIn('ABC123', seen)
            self.assertNotIn('XYZ456', seen)


class TestNoEmoji(unittest.TestCase):

    import re
    EMOJI = re.compile(
        r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2B00-\u2BFF\uFE0F]'
    )

    def test_query_strings_have_no_emoji(self):
        for _, _, qs in build_queries('all'):
            self.assertIsNone(self.EMOJI.search(qs), f"Emoji ditemukan di query: {qs}")


if __name__ == '__main__':
    unittest.main()
