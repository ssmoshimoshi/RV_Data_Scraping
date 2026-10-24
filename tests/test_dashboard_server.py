import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from scrapers.dashboard_server import enrich_lead_card, get_all_leads


class TestDashboardServer(unittest.TestCase):

    def test_enrich_lead_card(self):
        sample = {
            "business_name": "Test Cafe Kopi",
            "category": "fnb_beverage",
            "whatsapp_number": "6281234567890",
            "biography": "Best artisan coffee"
        }
        enriched = enrich_lead_card(sample)
        self.assertIn("score", enriched)
        self.assertIn("recommended_products", enriched)
        self.assertTrue(len(enriched["recommended_products"]) > 0)
        self.assertIn("pitch_text", enriched)
        self.assertIn("wa_link", enriched)
        self.assertTrue(enriched["wa_link"].startswith("https://wa.me/6281234567890"))

    def test_get_all_leads(self):
        leads = get_all_leads()
        self.assertIsInstance(leads, list)
        self.assertTrue(len(leads) > 0)
        for lead in leads:
            self.assertIn("business_name", lead)
            self.assertIn("score", lead)
            self.assertIn("recommended_products", lead)


if __name__ == "__main__":
    unittest.main()
