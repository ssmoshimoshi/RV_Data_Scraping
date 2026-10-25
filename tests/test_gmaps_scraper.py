import unittest
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import patch, MagicMock
from scrapers.gmaps_scraper import search_places, scrape_negative_reviews, _process_listing_data

class TestGmapsScraper(unittest.TestCase):
    def test_dry_run_returns_empty_list(self):
        result = search_places("test", "test", 1, True)
        self.assertEqual(result, [])

    @patch('scrapers.gmaps_scraper.ApifyClient')
    @patch.dict('os.environ', {'APIFY_API_TOKEN': 'test_token'})
    def test_search_places_stamps_platform_field(self, mock_client):
        mock_actor = MagicMock()
        mock_actor.call.return_value = {'defaultDatasetId': 'test_dataset'}
        mock_dataset = MagicMock()
        mock_dataset.iterate_items.return_value = [{
            'placeId': 'ChIJ123',
            'title': 'Butik Cantik',
            'categoryName': 'Clothing store',
            'address': 'Jl. Pettarani No. 1, Kota Makassar',
            'phone': '081234567890',
            'location': {'lat': -5.15, 'lng': 119.44},
            'reviews': [],
        }]
        mock_instance = mock_client.return_value
        mock_instance.actor.return_value = mock_actor
        mock_instance.dataset.return_value = mock_dataset

        result = search_places('butik', 'Makassar', 5, dry_run=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['platform'], 'google_maps')
        self.assertEqual(result[0]['title'], 'Butik Cantik')

    def test_scrape_negative_reviews_dry_run(self):
        result = scrape_negative_reviews("ChIJ12345", dry_run=True)
        self.assertEqual(result, [])

    def test_search_places_includes_packaging_and_commercials(self):
        item = {
            'placeId': '123',
            'reviews': [{'text': 'tutup cup bocor'}],
        }
        processed = _process_listing_data(item)
        
        self.assertIn('packaging_pain_points', processed)
        self.assertIn('estimated_commercials', processed)
        self.assertGreater(len(processed['packaging_pain_points']), 0)
        self.assertIn('est_monthly_units_min', processed['estimated_commercials'])

    def test_process_listing_data_extracts_multiple_pain_points(self):
        item = {
            'placeId': 'place_xyz',
            'title': 'Kopi Kenangan Senja',
            'categoryName': 'Coffee shop',
            'reviewsCount': 150,
            'reviews': [
                {'text': 'Kopi enak tapi tutup cup sering bocor dan tumpah', 'stars': 2, 'publishedAtDate': '2026-03-01'},
                {'text': 'Pelayanan ramah, tempat bersih', 'stars': 5, 'publishedAtDate': '2026-03-02'},
                {'text': 'Kemasan rusak dan sobek saat diantar kurir', 'stars': 1, 'publishedAtDate': '2026-03-03'}
            ]
        }
        processed = _process_listing_data(item)
        
        self.assertEqual(processed['category'], 'fnb_beverage')
        pain_points = processed['packaging_pain_points']
        self.assertEqual(len(pain_points), 2)
        
        first_kw = pain_points[0]['detected_keywords']
        self.assertTrue(any(k in first_kw for k in ['bocor', 'cup', 'tutup', 'tumpah']))
        self.assertEqual(pain_points[0]['rating'], 2)
        self.assertEqual(pain_points[0]['date'], '2026-03-01')
        
        second_kw = pain_points[1]['detected_keywords']
        self.assertTrue(any(k in second_kw for k in ['kemasan', 'rusak', 'sobek']))
        self.assertEqual(pain_points[1]['rating'], 1)

    def test_process_listing_data_no_packaging_issues(self):
        item = {
            'title': 'Toko Buku Pintar',
            'categoryName': 'Book store',
            'reviews': [
                {'text': 'Koleksi buku sangat lengkap dan murah', 'stars': 5},
                {'text': 'Tempat parkir agak sempit', 'stars': 3}
            ]
        }
        processed = _process_listing_data(item)
        self.assertEqual(len(processed['packaging_pain_points']), 0)
        self.assertIn('estimated_commercials', processed)

    def test_process_listing_data_commercial_tier_and_multiplier(self):
        item_high_reviews = {
            'title': 'Restoran Makassar Enak',
            'categoryName': 'Indonesian restaurant',
            'reviewsCount': 1200,
            'reviews': []
        }
        processed = _process_listing_data(item_high_reviews)
        self.assertEqual(processed['category'], 'fnb_food_resto')
        commercials = processed['estimated_commercials']
        self.assertEqual(commercials['priority_commercial_tier'], 'Tier 1 (High Value)')
        # 1200 reviews * 10 = 12000 > 10000 -> factor 1.5
        # fnb_food_resto base min units 1000 * 1.5 = 1500
        self.assertEqual(commercials['est_monthly_units_min'], 1500)
        self.assertEqual(commercials['restock_cycle_days'], 30)

    def test_process_listing_data_handles_empty_item(self):
        empty_item = {}
        processed = _process_listing_data(empty_item)
        self.assertEqual(processed['packaging_pain_points'], [])
        self.assertIn('estimated_commercials', processed)
        self.assertEqual(processed['category'], 'general_commercial')

if __name__ == '__main__':
    unittest.main()
