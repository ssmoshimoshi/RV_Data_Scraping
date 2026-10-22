import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from scrapers.meta_ads_scraper import extract_whatsapp_from_text, extract_external_links, search_meta_ads


class TestExtractWhatsAppFromText(unittest.TestCase):
    
    def test_extract_wa_with_prefix(self):
        text = "Hubungi kami di WA: 081234567890 untuk pemesanan"
        result = extract_whatsapp_from_text(text)
        self.assertEqual(result, '6281234567890')
    
    def test_extract_whatsapp_with_62(self):
        text = "Kontak: +62 812-3456-7890"
        result = extract_whatsapp_from_text(text)
        self.assertEqual(result, '6281234567890')
    
    def test_extract_multiple_numbers_first_valid(self):
        text = "Call us: 081234567890 or 021-87654321"
        result = extract_whatsapp_from_text(text)
        self.assertEqual(result, '6281234567890')
    
    def test_no_whatsapp_in_text(self):
        text = "Best coffee in town. Visit our store!"
        result = extract_whatsapp_from_text(text)
        self.assertIsNone(result)
    
    def test_extract_with_special_chars(self):
        text = "Order via WhatsApp: +62 (812) 345-6789"
        result = extract_whatsapp_from_text(text)
        self.assertEqual(result, '628123456789')
    
    def test_empty_text(self):
        result = extract_whatsapp_from_text('')
        self.assertIsNone(result)
    
    def test_none_text(self):
        result = extract_whatsapp_from_text(None)
        self.assertIsNone(result)


class TestExtractExternalLinks(unittest.TestCase):
    
    def test_extract_single_link(self):
        text = "Visit our website at https://example.com for more info"
        links = extract_external_links(text)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0], 'https://example.com')
    
    def test_extract_multiple_links(self):
        text = "Check https://example.com and http://shop.example.com"
        links = extract_external_links(text)
        self.assertEqual(len(links), 2)
    
    def test_extract_link_with_path(self):
        text = "Order here: https://wa.me/6281234567890"
        links = extract_external_links(text)
        self.assertEqual(len(links), 1)
        self.assertIn('wa.me', links[0])
    
    def test_no_links(self):
        text = "Just plain text without any links"
        links = extract_external_links(text)
        self.assertEqual(len(links), 0)
    
    def test_empty_text(self):
        links = extract_external_links('')
        self.assertEqual(len(links), 0)
    
    def test_none_text(self):
        links = extract_external_links(None)
        self.assertEqual(len(links), 0)


class TestSearchMetaAdsDryRun(unittest.TestCase):
    
    def test_dry_run_returns_empty_list(self):
        result = search_meta_ads('kuliner', limit=5, dry_run=True)
        self.assertEqual(result, [])


class TestMetaAdsDataStructure(unittest.TestCase):
    
    def test_ad_dict_structure(self):
        mock_ad_item = {
            'pageID': '123456789',
            'pageName': 'Cafe Kopi Kenangan',
            'adSnapshotURL': 'https://www.facebook.com/ads/library/?id=123456',
            'adCreativeBody': 'Promo spesial! Hubungi WA: 081234567890',
            'adDeliveryStartTime': '2026-10-01',
            'publisherPlatforms': ['instagram', 'facebook']
        }
        
        ad_body = mock_ad_item.get('adCreativeBody', '')
        whatsapp = extract_whatsapp_from_text(ad_body)
        links = extract_external_links(ad_body)
        
        ad_dict = {
            'page_id': mock_ad_item.get('pageID'),
            'page_name': mock_ad_item.get('pageName'),
            'ad_snapshot_url': mock_ad_item.get('adSnapshotURL'),
            'ad_creative_body': ad_body,
            'ad_delivery_start_time': mock_ad_item.get('adDeliveryStartTime'),
            'publisher_platforms': mock_ad_item.get('publisherPlatforms', []),
            'whatsapp_number': whatsapp,
            'external_links': links
        }
        
        self.assertEqual(ad_dict['page_id'], '123456789')
        self.assertEqual(ad_dict['page_name'], 'Cafe Kopi Kenangan')
        self.assertEqual(ad_dict['whatsapp_number'], '6281234567890')
        self.assertEqual(len(ad_dict['publisher_platforms']), 2)


if __name__ == '__main__':
    unittest.main()
