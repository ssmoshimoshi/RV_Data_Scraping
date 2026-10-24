import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from unittest.mock import patch, MagicMock
from pipeline import (
    run_threads_pipeline,
    run_food_delivery_pipeline,
    run_gmaps_pipeline,
    run_instagram_pipeline,
    run_meta_ads_pipeline,
    run_tiktok_pipeline
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

        run_tiktok_pipeline('food', 20, True, False)

        mock_scrape.assert_called_once()


if __name__ == '__main__':
    unittest.main()
