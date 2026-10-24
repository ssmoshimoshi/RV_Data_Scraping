import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date
from scrapers.threads_scraper import scrape_threads_profile


class TestThreadsScraper(unittest.TestCase):

    @patch('scrapers.threads_scraper.ApifyClient')
    @patch('scrapers.threads_scraper.os.getenv')
    def test_scrape_basic_profile(self, mock_getenv, mock_apify):
        mock_getenv.return_value = 'test_token'
        
        mock_client = MagicMock()
        mock_apify.return_value = mock_client
        
        mock_run = {'defaultDatasetId': 'dataset123'}
        mock_client.actor.return_value.call.return_value = mock_run
        
        mock_dataset = MagicMock()
        mock_client.dataset.return_value = mock_dataset
        
        mock_dataset.iterate_items.return_value = iter([{
            'full_name': 'Test Business',
            'biography': 'Test bio',
            'follower_count': 1000,
            'posts': [
                {'timestamp': '2026-10-20T10:00:00Z'},
                {'timestamp': '2026-10-19T10:00:00Z'}
            ]
        }])
        
        result = scrape_threads_profile('testuser', limit=10, dry_run=False)
        
        self.assertEqual(result['business_name'], 'Test Business')
        self.assertEqual(result['platform_handle'], 'testuser')
        self.assertEqual(result['biography'], 'Test bio')
        self.assertEqual(result['followers_count'], 1000)
        self.assertEqual(result['posts_count'], 2)
        self.assertTrue(result['is_active'])
        self.assertEqual(result['last_post_date'], '2026-10-20')

    @patch('scrapers.threads_scraper.ApifyClient')
    @patch('scrapers.threads_scraper.os.getenv')
    def test_normalize_whatsapp_in_profile(self, mock_getenv, mock_apify):
        mock_getenv.return_value = 'test_token'
        
        mock_client = MagicMock()
        mock_apify.return_value = mock_client
        
        mock_run = {'defaultDatasetId': 'dataset123'}
        mock_client.actor.return_value.call.return_value = mock_run
        
        mock_dataset = MagicMock()
        mock_client.dataset.return_value = mock_dataset
        
        mock_dataset.iterate_items.return_value = iter([{
            'full_name': 'Business With Phone',
            'phone_number': '+62812-3456-7890',
            'posts': []
        }])
        
        result = scrape_threads_profile('phoneuser', dry_run=False)
        
        self.assertEqual(result['whatsapp_number'], '6281234567890')

    def test_dry_run_mode(self):
        result = scrape_threads_profile('testuser', limit=5, dry_run=True)
        self.assertEqual(result, {})

    @patch('scrapers.threads_scraper.ApifyClient')
    @patch('scrapers.threads_scraper.os.getenv')
    def test_no_posts_inactive(self, mock_getenv, mock_apify):
        mock_getenv.return_value = 'test_token'
        
        mock_client = MagicMock()
        mock_apify.return_value = mock_client
        
        mock_run = {'defaultDatasetId': 'dataset123'}
        mock_client.actor.return_value.call.return_value = mock_run
        
        mock_dataset = MagicMock()
        mock_client.dataset.return_value = mock_dataset
        
        mock_dataset.iterate_items.return_value = iter([{
            'full_name': 'Inactive Business',
            'posts': []
        }])
        
        result = scrape_threads_profile('inactive', dry_run=False)
        
        self.assertFalse(result['is_active'])
        self.assertIsNone(result['last_post_date'])

    @patch('scrapers.threads_scraper.os.getenv')
    def test_missing_api_token(self, mock_getenv):
        mock_getenv.return_value = None
        
        with self.assertRaises(ValueError) as context:
            scrape_threads_profile('testuser', dry_run=False)
        
        self.assertIn('APIFY_API_TOKEN', str(context.exception))


if __name__ == '__main__':
    unittest.main()
