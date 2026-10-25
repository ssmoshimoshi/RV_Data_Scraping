import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from datetime import datetime, timedelta
from scrapers.tiktok_scraper import (
    extract_phone_from_bio,
    extract_hashtags,
    validate_recency,
    detect_relevant_hashtags,
    transform_to_lead_format
)


class TestTikTokScraperUtils(unittest.TestCase):
    
    def test_extract_phone_from_bio_standard(self):
        bio = "Order via WA 081234567890 sekarang juga"
        result = extract_phone_from_bio(bio)
        self.assertEqual(result, "6281234567890")
    
    def test_extract_phone_from_bio_with_62_prefix(self):
        bio = "Hubungi kami di 628567891234 untuk info lebih lanjut"
        result = extract_phone_from_bio(bio)
        self.assertEqual(result, "628567891234")
    
    def test_extract_phone_from_bio_no_phone(self):
        bio = "Toko hampers terbaik di Jakarta"
        result = extract_phone_from_bio(bio)
        self.assertIsNone(result)
    
    def test_extract_hashtags(self):
        text = "Video terbaru #kuliner #hamperslebaran #umkm"
        result = extract_hashtags(text)
        self.assertIn('#kuliner', result)
        self.assertIn('#hamperslebaran', result)
        self.assertEqual(len(result), 3)
    
    def test_validate_recency_active(self):
        recent_date = (datetime.now() - timedelta(days=15)).isoformat()
        result = validate_recency(recent_date, max_days=30)
        self.assertTrue(result)
    
    def test_validate_recency_inactive(self):
        old_date = (datetime.now() - timedelta(days=45)).isoformat()
        result = validate_recency(old_date, max_days=30)
        self.assertFalse(result)
    
    def test_detect_relevant_hashtags_positive(self):
        hashtags = ['#kuliner', '#hampers', '#trending']
        result = detect_relevant_hashtags(hashtags)
        self.assertTrue(result)
    
    def test_detect_relevant_hashtags_negative(self):
        hashtags = ['#fashion', '#beauty', '#travel']
        result = detect_relevant_hashtags(hashtags)
        self.assertFalse(result)
    
    def test_transform_to_lead_format(self):
        raw_data = [
            {
                'username': '@test_user',
                'display_name': 'Test User',
                'bio': 'Order WA 081234567890',
                'bio_link': 'https://linktr.ee/test',
                'is_seller_badge': True,
                'has_shop_link': True,
                'last_post_date': datetime.now().isoformat(),
                'hashtags': ['#kuliner', '#hampers']
            }
        ]
        
        leads = transform_to_lead_format(raw_data)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]['platform'], 'tiktok')
        self.assertEqual(leads[0]['username'], '@test_user')
        self.assertEqual(leads[0]['whatsapp_number'], '6281234567890')
        self.assertTrue(leads[0]['is_active'])
    
    def test_transform_filters_inactive_accounts(self):
        old_date = (datetime.now() - timedelta(days=45)).isoformat()
        raw_data = [
            {
                'username': '@inactive_user',
                'display_name': 'Inactive User',
                'bio': 'Old account',
                'bio_link': '',
                'is_seller_badge': False,
                'has_shop_link': False,
                'last_post_date': old_date,
                'hashtags': []
            }
        ]
        
        leads = transform_to_lead_format(raw_data)
        self.assertEqual(len(leads), 0)


class TestTikTokScraperSearch(unittest.TestCase):

    def test_scrape_tiktok_search_dry_run_empty(self):
        from scrapers.tiktok_scraper import scrape_tiktok_search
        res = scrape_tiktok_search('kemasan', limit=5, dry_run=True)
        self.assertEqual(res, [])

    def test_scrape_tiktok_search_fallback_to_mock(self):
        from scrapers.tiktok_scraper import scrape_tiktok_search
        from unittest.mock import patch
        with patch('scrapers.tiktok_scraper.scrape_tiktok_playwright', return_value=[]):
            res = scrape_tiktok_search('kemasan', limit=2, dry_run=False)
            self.assertEqual(len(res), 2)
            self.assertIn('@', res[0]['username'])


if __name__ == '__main__':
    unittest.main()
