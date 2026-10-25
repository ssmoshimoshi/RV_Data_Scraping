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

    def test_gofood_scrape_local(self):
        result = scrape_gofood('Makassar', 3, dry_run=False)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]['platform'], 'gofood')
        self.assertEqual(result[0]['city'], 'Makassar')
        self.assertIn('merchant_name', result[0])
        self.assertIn('classified_category', result[0])

    def test_grabfood_scrape_local(self):
        result = scrape_grabfood('Makassar', 3, dry_run=False)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]['platform'], 'grabfood')
        self.assertEqual(result[0]['city'], 'Makassar')
        self.assertIn('merchant_name', result[0])

    def test_shopeefood_scrape_local(self):
        result = scrape_shopeefood('Makassar', 3, dry_run=False)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]['platform'], 'shopeefood')
        self.assertEqual(result[0]['city'], 'Makassar')
        self.assertIn('merchant_name', result[0])

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

