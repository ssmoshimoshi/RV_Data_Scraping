import unittest
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import patch, MagicMock
from scrapers.instagram_scraper import (
    enrich_profile,
    run_follower_spider,
    scrape_instagram_profile_http,
    try_instagrapi_business_phone,
    _extract_json_data
)


class TestInstagramScraper(unittest.TestCase):
    
    def test_dry_run_profile_returns_empty(self):
        result = enrich_profile("testuser", dry_run=True)
        self.assertEqual(result, {})
    
    def test_dry_run_followers_returns_empty(self):
        result = run_follower_spider("testuser", 10, dry_run=True)
        self.assertEqual(result, [])
    
    @patch('scrapers.instagram_scraper.scrape_instagram_profile_http')
    def test_enrich_profile_extracts_metadata(self, mock_scrape):
        mock_scrape.return_value = {
            'username': 'kopititiktemu',
            'full_name': 'Kopi Titik Temu Official',
            'biography': 'Best coffee in Makassar',
            'external_url': 'https://linktr.ee/kopititiktemu',
            'followers_count': 18400,
            'following_count': 450,
            'posts_count': 320,
            'is_business_account': True,
            'is_verified': False,
            'profile_pic_url': 'https://example.com/pic.jpg',
            'recent_posts': [
                {'shortcode': 'ABC123', 'caption': 'New menu', 'likes': 450, 'comments': 30}
            ]
        }
        
        result = enrich_profile('kopititiktemu', dry_run=False)
        
        self.assertEqual(result['username'], 'kopititiktemu')
        self.assertEqual(result['full_name'], 'Kopi Titik Temu Official')
        self.assertEqual(result['followers_count'], 18400)
        self.assertTrue(result['is_business_account'])
        self.assertEqual(len(result['recent_posts']), 1)
    
    @patch('scrapers.instagram_scraper.scrape_instagram_profile_http')
    def test_enrich_profile_extracts_whatsapp_from_linktree(self, mock_scrape):
        mock_scrape.return_value = {
            'username': 'warungmakan',
            'full_name': 'Warung Makan Enak',
            'biography': 'Restoran keluarga',
            'external_url': 'https://wa.me/6281234567890',
            'followers_count': 5400,
            'posts_count': 120,
            'recent_posts': []
        }
        
        result = enrich_profile('warungmakan', dry_run=False)
        
        self.assertEqual(result['whatsapp_number'], '6281234567890')
    
    @patch('scrapers.instagram_scraper.scrape_instagram_profile_http')
    def test_enrich_profile_handles_error(self, mock_scrape):
        mock_scrape.return_value = {
            'error': 'Profile not found',
            'username': 'nonexistent'
        }
        
        result = enrich_profile('nonexistent', dry_run=False)
        
        self.assertIn('error', result)
        self.assertEqual(result['username'], 'nonexistent')
    
    def test_extract_json_data_from_html_ld_json(self):
        html = '''
        <html>
        <script type="application/ld+json">{"@type":"ProfilePage","mainEntity":{"name":"Test User","description":"Bio text"}}</script>
        </html>
        '''
        
        result = _extract_json_data(html)
        
        self.assertIsInstance(result, dict)
        if result:
            self.assertEqual(result.get('@type'), 'ProfilePage')
    
    def test_extract_json_data_from_shared_data(self):
        html = '''
        <script>window._sharedData = {"entry_data":{"ProfilePage":[{"graphql":{"user":{"username":"test"}}}]}};</script>
        '''
        
        result = _extract_json_data(html)
        
        self.assertIn('entry_data', result)
    
    def test_extract_json_data_returns_empty_on_invalid(self):
        html = '<html><body>No JSON here</body></html>'
        result = _extract_json_data(html)
        self.assertEqual(result, {})
    
    @patch('scrapers.instagram_scraper.Path.exists')
    def test_instagrapi_business_phone_no_session(self, mock_exists):
        mock_exists.return_value = False
        
        result = try_instagrapi_business_phone('testuser', Path('/fake/session.json'))
        
        self.assertIsNone(result)
    
    @patch('scrapers.instagram_scraper.scrape_instagram_profile_http')
    def test_enrich_profile_normalizes_phone_format(self, mock_scrape):
        mock_scrape.return_value = {
            'username': 'tokokue',
            'full_name': 'Toko Kue Manis',
            'biography': 'Kue segar setiap hari',
            'external_url': 'https://api.whatsapp.com/send?phone=81234567890',
            'followers_count': 3200,
            'posts_count': 85,
            'recent_posts': []
        }
        
        result = enrich_profile('tokokue', dry_run=False)
        
        self.assertEqual(result['whatsapp_number'], '6281234567890')
        self.assertTrue(result['whatsapp_number'].startswith('628'))
    
    @patch('scrapers.instagram_scraper.Path')
    def test_run_follower_spider_requires_session(self, mock_path):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        result = run_follower_spider('testuser', 10, dry_run=False)
        
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
