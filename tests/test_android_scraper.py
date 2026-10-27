import unittest
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import patch, MagicMock
from scrapers.android_scraper import (
    parse_count_metric,
    extract_instagram_profile,
    persist_profile_to_db
)


class TestAndroidScraper(unittest.TestCase):

    def test_parse_count_metric(self):
        self.assertEqual(parse_count_metric("680"), 680)
        self.assertEqual(parse_count_metric("27.7K"), 27700)
        self.assertEqual(parse_count_metric("1.5M"), 1500000)
        self.assertEqual(parse_count_metric("1,200"), 1200)
        self.assertEqual(parse_count_metric(None), 0)
        self.assertEqual(parse_count_metric("invalid"), 0)

    @patch("scrapers.android_scraper.upsert_lead")
    @patch("scrapers.android_scraper.init_db")
    def test_persist_profile_to_db(self, mock_init, mock_upsert):
        mock_init.return_value = True
        mock_upsert.return_value = True

        sample_data = {
            "username": "testcafe",
            "full_name": "Test Cafe Makassar",
            "business_category": "Coffee shop",
            "followers_count": 5000,
            "whatsapp_number": "6281234567890",
            "bio": "Tempat ngopi asik di Makassar",
            "address": "Jl. Somba Opu, Makassar",
            "website_url": "linktr.ee/testcafe",
            "is_wa_valid": 1
        }

        res = persist_profile_to_db(sample_data)
        self.assertTrue(res)
        mock_upsert.assert_called_once()
        call_arg = mock_upsert.call_args[0][0]
        self.assertEqual(call_arg["entity_id"], "ent_ig_testcafe")
        self.assertEqual(call_arg["business_name"], "Test Cafe Makassar")
        self.assertEqual(call_arg["whatsapp_number"], "6281234567890")


if __name__ == "__main__":
    unittest.main()
