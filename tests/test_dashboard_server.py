import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import http.client
import json
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from scrapers.dashboard_server import (
    DashboardHandler,
    enrich_lead_card,
    get_all_leads,
    load_processed_dossiers,
)

SAMPLE_ENTITY = {
    "entity_id": "ent_0001",
    "business_name": "Warung Coto Daeng",
    "city": "makassar",
    "district_area": "panakkukang",
    "whatsapp_number": "6281234567890",
    "platforms": ["google_maps", "gofood"],
    "lead_score": 85,
    "priority_tier": "Tier A",
    "whatsapp_pitch": "Halo Warung Coto Daeng di Makassar, perkenalkan kami RUANG VISUAL.",
    "records": [{
        "platform": "google_maps",
        "title": "Warung Coto Daeng",
        "address": "Jl. Pettarani No. 1",
        "latitude": -5.15,
        "longitude": 119.44,
        "estimated_commercials": {"est_monthly_units_min": 1000, "est_monthly_units_max": 3000},
        "packaging_pain_points": [{"review_text": "kuah bocor", "detected_keywords": ["bocor", "kuah"]}],
    }],
}


class TestLoadProcessedDossiers(unittest.TestCase):

    def test_reads_latest_unified_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([SAMPLE_ENTITY], ensure_ascii=False), encoding="utf-8")
            leads = load_processed_dossiers(Path(tmp))
            self.assertEqual(len(leads), 1)
            lead = leads[0]
            self.assertEqual(lead["id"], "ent_0001")
            self.assertEqual(lead["business_name"], "Warung Coto Daeng")
            self.assertEqual(lead["lead_score"], 85)
            self.assertEqual(lead["priority_tier"], "Tier A")
            self.assertEqual(lead["platforms"], ["google_maps", "gofood"])
            self.assertEqual(lead["estimated_commercials"]["est_monthly_units_min"], 1000)
            self.assertEqual(lead["packaging_pain_points"][0]["detected_keywords"], ["bocor", "kuah"])
            self.assertIn("RUANG VISUAL", lead["whatsapp_pitch"])
            self.assertEqual(lead["status"], "ready_to_pitch")

    def test_empty_dir_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_processed_dossiers(Path(tmp)), [])

    def test_broken_json_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json").write_text("rusak", encoding="utf-8")
            self.assertEqual(load_processed_dossiers(Path(tmp)), [])


class TestExportCsvEndpoint(unittest.TestCase):

    def setUp(self):
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), DashboardHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _get(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path)
        res = conn.getresponse()
        body = res.read()
        conn.close()
        return res, body

    def test_export_csv_returns_200_with_csv_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            fixture.write_text(json.dumps([SAMPLE_ENTITY], ensure_ascii=False), encoding="utf-8")
            out_csv = Path(tmp) / "data" / "processed" / "dossiers_export_ruang_visual.csv"
            with patch("scrapers.dashboard_server.find_latest_dossier", return_value=fixture), \
                 patch("scrapers.dashboard_server.PROJECT_ROOT", Path(tmp)):
                res, body = self._get("/api/export/csv")
            self.assertEqual(res.status, 200)
            self.assertIn("text/csv", res.getheader("Content-Type"))
            self.assertIn('attachment; filename="dossiers_export_ruang_visual.csv"', res.getheader("Content-Disposition"))
            self.assertEqual(res.getheader("Access-Control-Allow-Origin"), "*")
            self.assertIn(b"entity_id", body)
            self.assertIn(b"Warung Coto Daeng", body)
            self.assertTrue(out_csv.exists())

    def test_export_csv_returns_404_when_no_dossier(self):
        with patch("scrapers.dashboard_server.find_latest_dossier", return_value=None):
            res, body = self._get("/api/export/csv")
        self.assertEqual(res.status, 404)
        self.assertIn("error", json.loads(body))


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
