import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from datetime import datetime, date
from scrapers.threads_scraper import scrape_threads_profile


class TestThreadsScraper(unittest.TestCase):

    def test_scrape_basic_profile_local(self):
        result = scrape_threads_profile('testuser', limit=10, dry_run=False)

        self.assertIsNotNone(result)
        self.assertIn('business_name', result)
        self.assertEqual(result['platform_handle'], 'testuser')
        self.assertIn('biography', result)
        self.assertIn('followers_count', result)
        self.assertIn('posts_count', result)
        self.assertIn('is_active', result)
        self.assertIn('last_post_date', result)

    def test_whatsapp_extraction_from_bio(self):
        result = scrape_threads_profile('phoneuser', dry_run=False)
        
        self.assertIn('whatsapp_number', result)
        if result['whatsapp_number']:
            self.assertTrue(result['whatsapp_number'].startswith('628'))

    def test_dry_run_mode(self):
        result = scrape_threads_profile('testuser', limit=5, dry_run=True)
        self.assertEqual(result, {})


if __name__ == '__main__':
    unittest.main()
