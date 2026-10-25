import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pipeline import (
    run_threads_pipeline,
    run_food_delivery_pipeline,
    run_gmaps_pipeline,
    run_instagram_pipeline,
    run_meta_ads_pipeline,
    run_tiktok_pipeline,
    run_match_pipeline,
    run_export_pipeline,
    run_harvest_pipeline
)


class TestThreadsPipeline(unittest.TestCase):
    @patch('pipeline.scrape_threads_profile')
    @patch('pipeline.insert_lead')
    @patch('pipeline.calculate_score')
    @patch('pipeline.qualify_lead')
    @patch('pipeline.classify_category')
    def test_threads_pipeline_qualified_lead(self, mock_classify, mock_qualify, mock_score, mock_insert, mock_scrape):
        mock_scrape.return_value = {
            'business_name': 'Test Cafe',
            'whatsapp_number': '6281234567890',
            'biography': 'Coffee shop in Jakarta',
            'last_post_date': '2026-10-20',
            'is_active': True
        }
        mock_classify.return_value = 'Food & Beverage'
        mock_qualify.return_value = (True, '')
        mock_score.return_value = 85
        mock_insert.return_value = (True, 'Success')

        run_threads_pipeline('testcafe', 10, False, True)

        mock_scrape.assert_called_once_with(username='testcafe', limit=10, dry_run=False)
        mock_qualify.assert_called_once()
        mock_insert.assert_called_once()

    @patch('pipeline.scrape_threads_profile')
    @patch('pipeline.qualify_lead')
    def test_threads_pipeline_disqualified_lead(self, mock_qualify, mock_scrape):
        mock_scrape.return_value = {
            'business_name': 'Personal Account',
            'whatsapp_number': None,
            'biography': 'Just a personal blog',
            'last_post_date': None,
            'is_active': False
        }
        mock_qualify.return_value = (False, 'No contact info')

        run_threads_pipeline('personal', 10, False, False)

        mock_scrape.assert_called_once()
        mock_qualify.assert_called_once()

    @patch('pipeline.scrape_threads_profile')
    def test_threads_pipeline_dry_run(self, mock_scrape):
        mock_scrape.return_value = {}

        run_threads_pipeline('test', 10, True, False)

        mock_scrape.assert_called_once_with(username='test', limit=10, dry_run=True)


class TestFoodDeliveryPipeline(unittest.TestCase):
    @patch('pipeline.scrape_gofood')
    @patch('pipeline.insert_lead')
    @patch('pipeline.calculate_score')
    @patch('pipeline.qualify_lead')
    def test_gofood_pipeline_qualified(self, mock_qualify, mock_score, mock_insert, mock_scrape):
        mock_scrape.return_value = [{
            'merchant_id': 'gf123',
            'merchant_name': 'Warung Makan Sedap',
            'phone_number': '6281234567890',
            'address_full': 'Jl. Raya No. 10',
            'district_area': 'Panakkukang',
            'city': 'Makassar',
            'category': 'Food & Beverage',
            'platform': 'gofood'
        }]
        mock_qualify.return_value = (True, '')
        mock_score.return_value = 75
        mock_insert.return_value = (True, 'Success')

        run_food_delivery_pipeline('gofood', 'Makassar', 20, False, True)

        mock_scrape.assert_called_once_with(city='Makassar', limit=20, dry_run=False)
        mock_qualify.assert_called_once()
        mock_insert.assert_called_once()

    @patch('pipeline.scrape_grabfood')
    @patch('pipeline.qualify_lead')
    def test_grabfood_pipeline_disqualified(self, mock_qualify, mock_scrape):
        mock_scrape.return_value = [{
            'merchant_id': 'grab456',
            'merchant_name': 'No Contact Resto',
            'phone_number': None,
            'address_full': '',
            'district_area': '',
            'city': 'Jakarta',
            'category': 'Food & Beverage',
            'platform': 'grabfood'
        }]
        mock_qualify.return_value = (False, 'No phone number')

        run_food_delivery_pipeline('grabfood', 'Jakarta', 10, False, False)

        mock_scrape.assert_called_once()
        mock_qualify.assert_called_once()

    @patch('pipeline.scrape_shopeefood')
    def test_shopeefood_pipeline_dry_run(self, mock_scrape):
        mock_scrape.return_value = []

        run_food_delivery_pipeline('shopeefood', 'Surabaya', 15, True, False)

        mock_scrape.assert_called_once_with(city='Surabaya', limit=15, dry_run=True)

    def test_unknown_platform(self):
        run_food_delivery_pipeline('unknown', 'Jakarta', 10, False, False)


class TestExistingPipelines(unittest.TestCase):
    @patch('pipeline.search_places')
    @patch('pipeline.insert_lead')
    def test_gmaps_pipeline_dry_run(self, mock_insert, mock_search):
        mock_search.return_value = []

        run_gmaps_pipeline('cafe', 'Makassar', 10, True, False)

        mock_search.assert_called_once()
        mock_insert.assert_not_called()

    @patch('pipeline.enrich_profile')
    def test_instagram_pipeline_dry_run(self, mock_enrich):
        mock_enrich.return_value = {}

        run_instagram_pipeline('testuser', 50, True, False)

        mock_enrich.assert_called_once()

    @patch('pipeline.search_meta_ads')
    def test_meta_ads_pipeline_dry_run(self, mock_search):
        mock_search.return_value = []

        run_meta_ads_pipeline('fashion', 10, True, False)

        mock_search.assert_called_once()

    @patch('pipeline.scrape_tiktok_search')
    def test_tiktok_pipeline_dry_run(self, mock_scrape):
        mock_scrape.return_value = []

        run_tiktok_pipeline('kuliner', 10, True, False)

        mock_scrape.assert_called_once()

    @patch('pipeline.harvest')
    def test_harvest_pipeline(self, mock_harvest):
        run_harvest_pipeline('fnb', 5, True)
        mock_harvest.assert_called_once_with(sector='fnb', limit_per_query=5, dry_run=True)


class TestMatchPipeline(unittest.TestCase):
    RAW_RECORDS = [
        {'platform': 'google_maps', 'title': 'Squid Coffee', 'whatsapp_number': '628170772777', 'city': 'Makassar'},
        {'platform': 'tiktok', 'display_name': 'squid.coffee', 'whatsapp_number': '08170772777'},
    ]

    def _prepare(self, tmp):
        raw_dir = Path(tmp) / 'raw'
        raw_dir.mkdir()
        (raw_dir / 'sample.json').write_text(json.dumps(self.RAW_RECORDS), encoding='utf-8')
        return raw_dir, Path(tmp) / 'out'

    def test_match_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir, out_dir = self._prepare(tmp)
            run_match_pipeline(str(raw_dir), str(out_dir), 'Makassar', True)
            self.assertFalse(out_dir.exists())

    def test_match_writes_unified_dossiers_with_pitch(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir, out_dir = self._prepare(tmp)
            run_match_pipeline(str(raw_dir), str(out_dir), 'Makassar', False)
            files = list(out_dir.glob('unified_dossiers_Makassar_*.json'))
            self.assertEqual(len(files), 1)
            entities = json.loads(files[0].read_text(encoding='utf-8'))
            self.assertEqual(len(entities), 1)
            self.assertIn('whatsapp_pitch', entities[0])
            self.assertIn('Squid Coffee', entities[0]['whatsapp_pitch'])

    def test_match_writes_valid_lead_score_and_tier(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir, out_dir = self._prepare(tmp)
            run_match_pipeline(str(raw_dir), str(out_dir), 'Makassar', False)
            entities = json.loads(next(out_dir.glob('unified_dossiers_*.json')).read_text(encoding='utf-8'))
            for ent in entities:
                self.assertIsInstance(ent['lead_score'], int)
                self.assertTrue(0 <= ent['lead_score'] <= 100)
                expected = ('Tier A' if ent['lead_score'] >= 80 else
                            'Tier B' if ent['lead_score'] >= 60 else
                            'Tier C' if ent['lead_score'] >= 40 else 'Tier D')
                self.assertEqual(ent['priority_tier'], expected)

    def test_match_export_csv_lead_score_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir, out_dir = self._prepare(tmp)
            run_match_pipeline(str(raw_dir), str(out_dir), 'Makassar', False)
            json_path = next(out_dir.glob('unified_dossiers_*.json'))
            out_csv = Path(tmp) / 'hasil.csv'
            run_export_pipeline(str(json_path), str(out_csv), False)
            with out_csv.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertIn('whatsapp_pitch', rows[0])
            self.assertNotEqual(rows[0]['whatsapp_pitch'], '')

    def test_match_empty_raw_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_match_pipeline(tmp, str(Path(tmp) / 'out'), 'Makassar', False)
            self.assertFalse(Path(tmp, 'out').exists())


class TestExportPipeline(unittest.TestCase):
    DOSSIERS = [{
        'entity_id': 'ent_0001',
        'business_name': 'Squid Coffee',
        'city': 'makassar',
        'whatsapp_number': '628170772777',
        'platforms': ['google_maps', 'tiktok'],
        'whatsapp_pitch': 'Halo Squid Coffee di Makassar, perkenalkan kami RUANG VISUAL.',
        'records': [],
    }]

    def test_export_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / 'unified_dossiers_Makassar_20261025_000000.json'
            json_path.write_text(json.dumps(self.DOSSIERS), encoding='utf-8')
            out_csv = Path(tmp) / 'hasil.csv'
            run_export_pipeline(str(json_path), str(out_csv), True)
            self.assertFalse(out_csv.exists())

    def test_export_writes_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / 'unified_dossiers_Makassar_20261025_000000.json'
            json_path.write_text(json.dumps(self.DOSSIERS), encoding='utf-8')
            out_csv = Path(tmp) / 'hasil.csv'
            run_export_pipeline(str(json_path), str(out_csv), False)
            self.assertTrue(out_csv.exists())
            content = out_csv.read_text(encoding='utf-8')
            self.assertIn('entity_id', content)
            self.assertIn('Squid Coffee', content)

    def test_export_missing_input_graceful(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_export_pipeline(str(Path(tmp) / 'tidak_ada.json'), str(Path(tmp) / 'x.csv'), False)

    def test_export_include_no_wa_flag(self):
        mixed = [
            {'entity_id': 'ent_0001', 'business_name': 'Ada WA', 'whatsapp_number': '62811111111', 'records': []},
            {'entity_id': 'ent_0002', 'business_name': 'Tanpa WA', 'whatsapp_number': '', 'records': []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / 'dossiers.json'
            json_path.write_text(json.dumps(mixed), encoding='utf-8')
            out_csv = Path(tmp) / 'sales.csv'
            run_export_pipeline(str(json_path), str(out_csv), False, include_no_wa=True)
            with out_csv.open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)


if __name__ == '__main__':
    unittest.main()
