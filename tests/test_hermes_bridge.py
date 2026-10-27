import unittest
from unittest.mock import patch, MagicMock
from scrapers.sync_hermes import (
    format_lead_for_radar_prospek,
    sync_leads_to_hermes,
    send_webhook_payload,
    RADAR_PROSPEK_HEADERS,
)
from scrapers.sample_leads import SAMPLE_LEADS


class TestHermesBridge(unittest.TestCase):

    def test_format_lead_for_radar_prospek_has_14_columns(self):
        lead = SAMPLE_LEADS[0]
        row = format_lead_for_radar_prospek(lead)
        self.assertEqual(len(row), 14)
        self.assertEqual(len(row), len(RADAR_PROSPEK_HEADERS))
        self.assertEqual(row[0], "Kopi Titik Temu Makassar")
        self.assertTrue(row[5].startswith("628"))
        self.assertTrue("wa.me" in row[6])
        self.assertNotEqual(row[7], "-")
        self.assertTrue(len(row[13]) == 10)

    def test_sync_leads_dry_run_returns_expected_structure(self):
        res = sync_leads_to_hermes(leads=SAMPLE_LEADS[:3], dry_run=True)
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["rows_count"], 3)
        self.assertEqual(len(res["sample_rows"]), 2)
        self.assertEqual(len(res["sample_rows"][0]), 14)

    def test_sync_leads_handles_custom_leads(self):
        custom_lead = {
            "id": "custom-01",
            "business_name": "Kedai Roti Tradisional",
            "category": "fnb_restaurant",
            "whatsapp_number": "628999888777",
            "address_full": "Jl. Pengayoman No.10, Makassar",
            "rating": 4.8,
            "reviews_count": 45,
            "platform": "google_maps",
            "latitude": -5.14,
            "longitude": 119.43,
        }
        row = format_lead_for_radar_prospek(custom_lead)
        self.assertEqual(len(row), 14)
        self.assertEqual(row[0], "Kedai Roti Tradisional")
        self.assertEqual(row[5], "628999888777")
        self.assertIn("https://wa.me/628999888777", row[6])

    @patch("urllib.request.urlopen")
    def test_send_webhook_payload_mocked(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok", "appended": 6}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        payload = {"sheet_name": "Radar Prospek", "action": "append", "rows": [["test"]]}
        res = send_webhook_payload(payload, webhook_url="https://script.google.com/macros/s/dummy/exec")
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res.get("appended"), 6)

    def test_send_webhook_payload_requires_url(self):
        with self.assertRaises(ValueError):
            send_webhook_payload({"action": "ping"}, webhook_url="")


if __name__ == "__main__":
    unittest.main()
