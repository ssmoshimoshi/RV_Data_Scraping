import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from unittest.mock import patch, MagicMock
from scrapers.food_delivery_scraper import (
    scrape_gofood,
    scrape_grabfood,
    scrape_shopeefood,
    scrape_all,
    _extract_dataset_id,
    _process_merchant_data
)


class TestFoodDeliveryScraper(unittest.TestCase):

    def test_dry_run_gofood(self):
        result = scrape_gofood('Makassar', 10, dry_run=True)
        self.assertEqual(result, [])

    def test_dry_run_grabfood(self):
        result = scrape_grabfood('Makassar', 10, dry_run=True)
        self.assertEqual(result, [])

    def test_dry_run_shopeefood(self):
        result = scrape_shopeefood('Makassar', 10, dry_run=True)
        self.assertEqual(result, [])

    def test_dry_run_all(self):
        result = scrape_all('Makassar', 10, dry_run=True)
        self.assertIn('gofood', result)
        self.assertIn('grabfood', result)
        self.assertIn('shopeefood', result)
        self.assertEqual(result['gofood'], [])
        self.assertEqual(result['grabfood'], [])
        self.assertEqual(result['shopeefood'], [])

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_api_token_gofood(self):
        with self.assertRaises(ValueError):
            scrape_gofood('Makassar', 10, dry_run=False)

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_api_token_grabfood(self):
        with self.assertRaises(ValueError):
            scrape_grabfood('Makassar', 10, dry_run=False)

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_api_token_shopeefood(self):
        with self.assertRaises(ValueError):
            scrape_shopeefood('Makassar', 10, dry_run=False)

    @patch('scrapers.food_delivery_scraper.ApifyClient')
    @patch.dict('os.environ', {'APIFY_API_TOKEN': 'test_token'})
    def test_gofood_scrape_with_mock(self, mock_client):
        mock_actor = MagicMock()
        mock_run = {'defaultDatasetId': 'test_dataset'}
        mock_actor.call.return_value = mock_run

        mock_dataset = MagicMock()
        mock_dataset.iterate_items.return_value = [
            {
                'id': 'merchant123',
                'name': 'Warung Makan Sederhana',
                'address': 'Jl. Sudirman No. 45, Kota Makassar',
                'phone': '081234567890',
                'category': 'Indonesian Food'
            }
        ]

        mock_instance = mock_client.return_value
        mock_instance.actor.return_value = mock_actor
        mock_instance.dataset.return_value = mock_dataset

        result = scrape_gofood('Makassar', 10, dry_run=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['merchant_name'], 'Warung Makan Sederhana')
        self.assertEqual(result[0]['phone_number'], '6281234567890')
        self.assertEqual(result[0]['platform'], 'gofood')
        self.assertEqual(result[0]['city'], 'Makassar')
        self.assertIn('estimated_commercials', result[0])
        self.assertIn('packaging_pain_points', result[0])

    @patch('scrapers.food_delivery_scraper.ApifyClient')
    @patch.dict('os.environ', {'APIFY_API_TOKEN': 'test_token'})
    def test_grabfood_scrape_with_mock(self, mock_client):
        mock_actor = MagicMock()
        mock_run = {'defaultDatasetId': 'test_dataset'}
        mock_actor.call.return_value = mock_run

        mock_dataset = MagicMock()
        mock_dataset.iterate_items.return_value = [
            {
                'id': 'grab456',
                'restaurantName': 'Cafe Kopi Makassar',
                'address': 'Jl. Veteran, Kec. Panakkukang, Kota Makassar',
                'phoneNumber': '0411-8765432',
                'category': 'Cafe'
            }
        ]

        mock_instance = mock_client.return_value
        mock_instance.actor.return_value = mock_actor
        mock_instance.dataset.return_value = mock_dataset

        result = scrape_grabfood('Makassar', 10, dry_run=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['merchant_name'], 'Cafe Kopi Makassar')
        self.assertIsNone(result[0]['phone_number'])
        self.assertEqual(result[0]['platform'], 'grabfood')
        self.assertEqual(result[0]['district_area'], 'Panakkukang')

    def test_extract_dataset_id_variants(self):
        # Dictionary format
        self.assertEqual(_extract_dataset_id({'defaultDatasetId': 'ds_1'}), 'ds_1')
        self.assertEqual(_extract_dataset_id({'default_dataset_id': 'ds_2'}), 'ds_2')
        # Object format
        class MockRun:
            default_dataset_id = 'ds_3'
        self.assertEqual(_extract_dataset_id(MockRun()), 'ds_3')
        # None
        self.assertEqual(_extract_dataset_id(None), '')

    def test_process_merchant_data_with_pain_points(self):
        item = {
            'restaurantName': 'Mie Pedas Makassar',
            'category': 'Restoran',
            'reviews': [
                {'text': 'Kuah tumpah dan kotak box lembek basah kuyup', 'rating': 1},
                {'text': 'Rasa enak mantap', 'rating': 5}
            ]
        }
        res = _process_merchant_data(item)
        self.assertEqual(res['classified_category'], 'fnb_food_resto')
        self.assertEqual(len(res['packaging_pain_points']), 1)
        self.assertIn('tumpah', res['packaging_pain_points'][0]['detected_keywords'])
        self.assertIn('box', res['packaging_pain_points'][0]['detected_keywords'])
        self.assertEqual(res['estimated_commercials']['priority_commercial_tier'], 'Tier 1 (High Value)')
        self.assertEqual(res['estimated_commercials']['restock_cycle_days'], 30)


if __name__ == '__main__':
    unittest.main()

