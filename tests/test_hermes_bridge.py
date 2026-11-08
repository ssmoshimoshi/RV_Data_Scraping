import unittest
from unittest.mock import patch, MagicMock
from scrapers.sync_hermes import (
    format_lead_for_radar_prospek,
    sync_leads_to_hermes,
    pull_leads_from_hermes,
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

    @patch("scrapers.sync_hermes.fetch_sheet_rows")
    def test_pull_leads_from_hermes_mocked(self, mock_fetch):
        mock_fetch.return_value = [
            ["Nama Bisnis", "Kategori", "Sumber Platform", "Skor", "Status", "No. WhatsApp", "Link WA", "Proyeksi Kebutuhan Cetak", "Pemicu", "Alamat", "Rating & Ulasan", "Website", "Link Peta", "Tanggal"],
            ["Warung Baru Makassar", "Fnb Hospitality", "Google Maps", "60", "Tier C (Skor 60)", "6281234567890", "wa.me", "Paper Cup", "Pemicu", "Jl. Pettarani No. 1", "4.8 (50 ulasan)", "-", "https://maps.google.com", "2026-10-29"],
        ]
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_db = Path(tmp_dir) / "test_leads.sqlite"
            res = pull_leads_from_hermes(sheet_name="Radar Prospek", db_path=str(temp_db), dry_run=False)
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["imported_count"], 1)
            self.assertEqual(res["updated_count"], 0)

            # Test second pull (update)
            res_update = pull_leads_from_hermes(sheet_name="Radar Prospek", db_path=str(temp_db), dry_run=False)
            self.assertEqual(res_update["imported_count"], 0)
            self.assertEqual(res_update["updated_count"], 1)


if __name__ == "__main__":
    unittest.main()
