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
    build_channels_from_records,
    persist_channel_to_dossier,
    persist_status_to_dossier,
    inspect_account_content,
    VALID_OUTREACH_STATUSES,
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
        "total_score": 4.8,
        "reviews_count": 420,
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
            self.assertEqual(lead["rating"], 4.8)
            self.assertEqual(lead["reviews_count"], 420)

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


MULTI_CHANNEL_ENTITY = {
    "entity_id": "ent_0002",
    "business_name": "Kopi Kanal Lengkap",
    "city": "makassar",
    "district_area": "panakkukang",
    "whatsapp_number": "6281234567891",
    "platforms": ["google_maps", "instagram", "tiktok", "gofood"],
    "records": [
        {"platform": "google_maps", "title": "Kopi Kanal Lengkap", "place_id": "ChIJ_abc123", "address": "Jl. Boulevard No. 2"},
        {"platform": "instagram", "website": "https://www.instagram.com/kopikanal"},
        {"platform": "tiktok", "platform_handle": "kopikanallengkap"},
        {"platform": "gofood", "title": "Kopi Kanal Lengkap"},
    ],
}


class TestBuildChannels(unittest.TestCase):

    def test_channels_mapped_from_records(self):
        records = MULTI_CHANNEL_ENTITY["records"]
        channels = build_channels_from_records(MULTI_CHANNEL_ENTITY, records, records[0])
        self.assertEqual(channels["google_maps"], "https://www.google.com/maps/place/?q=place_id:ChIJ_abc123")
        self.assertEqual(channels["instagram"], "https://www.instagram.com/kopikanal")
        self.assertEqual(channels["tiktok"], "https://www.tiktok.com/@kopikanallengkap")
        self.assertEqual(channels["threads"], "")
        self.assertEqual(channels["food_delivery"], "GoFood")

    def test_google_maps_fallback_to_website_url(self):
        ent = {}
        rec = {"platform": "google_maps", "website": "https://www.google.com/maps/place/?cid=999"}
        channels = build_channels_from_records(ent, [rec], rec)
        self.assertEqual(channels["google_maps"], "https://www.google.com/maps/place/?cid=999")

    def test_no_data_returns_empty_channels(self):
        channels = build_channels_from_records({}, [], {})
        self.assertEqual(channels, {
            "google_maps": "", "instagram": "", "tiktok": "", "threads": "", "food_delivery": "",
        })

    def test_load_processed_dossiers_includes_channels_and_top_posts(self):
        ent = dict(MULTI_CHANNEL_ENTITY)
        ent["top_posts"] = [{"id": "post-x", "caption": "Kemasan baru", "views": 100, "likes": 10,
                             "comments": 2, "engagement_rate": 5.0, "date": "2026-10-20",
                             "packaging_signal": True, "tags": ["Box"]}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([ent], ensure_ascii=False), encoding="utf-8")
            leads = load_processed_dossiers(Path(tmp))
            self.assertEqual(len(leads), 1)
            lead = leads[0]
            self.assertEqual(lead["channels"]["instagram"], "https://www.instagram.com/kopikanal")
            self.assertEqual(lead["channels"]["google_maps"],
                             "https://www.google.com/maps/place/?q=place_id:ChIJ_abc123")
            self.assertEqual(lead["top_posts"][0]["id"], "post-x")

    def test_load_processed_dossiers_without_top_posts_defaults_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")
            lead = load_processed_dossiers(Path(tmp))[0]
            self.assertEqual(lead["top_posts"], [])


class TestPersistChannelToDossier(unittest.TestCase):

    def test_persist_updates_dossier_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")
            posts = [{"id": "post-1", "caption": "Uji coba", "views": 10, "likes": 2,
                      "comments": 1, "engagement_rate": 3.0, "date": "2026-10-25",
                      "packaging_signal": False, "tags": []}]
            ok = persist_channel_to_dossier("ent_0002", "instagram", "kopikanal", posts, Path(tmp))
            self.assertTrue(ok)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["channels"]["instagram"], "kopikanal")
            self.assertEqual(saved[0]["top_posts"], posts)
            self.assertTrue(saved[0]["is_active_verified"])
            self.assertIn("latest_post_date", saved[0])

    def test_persist_unknown_entity_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")
            self.assertFalse(persist_channel_to_dossier("ent_9999", "instagram", "x", [], Path(tmp)))

    def test_persist_without_dossier_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(persist_channel_to_dossier("ent_0002", "instagram", "x", [], Path(tmp)))


class TestLinkChannelEndpoint(unittest.TestCase):

    def setUp(self):
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), DashboardHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _post(self, path, payload):
        body = json.dumps(payload).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res, data

    def test_link_channel_on_dossier_lead_succeeds_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            fixture.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")
            with patch("scrapers.dashboard_server.find_latest_dossier", return_value=fixture):
                res, body = self._post("/api/leads/link-channel", {
                    "lead_id": "ent_0002",
                    "platform": "instagram",
                    "handle_or_url": "https://instagram.com/kopikanalbaru",
                })
            self.assertEqual(res.status, 200)
            data = json.loads(body)
            self.assertEqual(data["status"], "success")
            self.assertTrue(data["persisted"])
            self.assertEqual(len(data["inspection"]["posts"]), 0)
            self.assertEqual(data["inspection"]["status"], "Belum diinspeksi")
            self.assertEqual(data["lead"]["channels"]["instagram"], "kopikanalbaru")
            saved = json.loads(fixture.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["channels"]["instagram"], "kopikanalbaru")
            self.assertEqual(len(saved[0]["top_posts"]), 0)

    def test_link_channel_on_sample_lead_still_works(self):
        res, body = self._post("/api/leads/link-channel", {
            "lead_id": "lead-001",
            "platform": "tiktok",
            "handle_or_url": "titiktemu_baru",
        })
        self.assertEqual(res.status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["persisted"])
        self.assertEqual(data["lead"]["channels"]["tiktok"], "titiktemu_baru")

    def test_link_channel_unknown_lead_returns_404(self):
        with patch("scrapers.dashboard_server.find_latest_dossier", return_value=None):
            res, body = self._post("/api/leads/link-channel", {
                "lead_id": "lead-tidak-ada",
                "platform": "instagram",
                "handle_or_url": "entah",
            })
        self.assertEqual(res.status, 404)
        self.assertIn("error", json.loads(body))

    def test_inspect_account_content_factual_empty(self):
        result = inspect_account_content("instagram", "kopititiktemu", "Kopi Titik Temu")
        self.assertEqual(result["status"], "Belum diinspeksi")
        self.assertEqual(result["posts"], [])
        self.assertEqual(result["total_analyzed_posts"], 0)
        self.assertEqual(result["total_views"], 0)
        self.assertEqual(result["avg_engagement_rate"], 0.0)
        self.assertEqual(result["commercial_velocity"], "Tidak Terdeteksi")

    def test_inspect_content_endpoint_returns_factual_status(self):
        res, body = self._post("/api/inspect-content", {
            "platform": "instagram",
            "handle": "kopititiktemu",
            "business_name": "Kopi Titik Temu"
        })
        self.assertEqual(res.status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "Belum diinspeksi")
        self.assertEqual(data["posts"], [])
        self.assertEqual(data["total_analyzed_posts"], 0)


class TestPersistStatusToDossier(unittest.TestCase):

    def test_persist_status_success_with_dihubungi(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")

            ok = persist_status_to_dossier("ent_0002", "Dihubungi", "Sudah kirim pesan WA ke owner", Path(tmp))
            self.assertTrue(ok)

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["outreach_status"], "Dihubungi")
            self.assertEqual(saved[0]["outreach_notes"], "Sudah kirim pesan WA ke owner")
            self.assertIsNotNone(saved[0].get("contacted_at"))

    def test_persist_status_closing_sets_contacted_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")

            ok = persist_status_to_dossier("ent_0002", "Closing", "Pesanan 1000 cup disetujui", Path(tmp))
            self.assertTrue(ok)

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["outreach_status"], "Closing")
            self.assertEqual(saved[0]["outreach_notes"], "Pesanan 1000 cup disetujui")
            self.assertIsNotNone(saved[0].get("contacted_at"))

    def test_persist_status_other_does_not_set_contacted_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")

            ok = persist_status_to_dossier("ent_0002", "Tertarik", "Tanya daftar harga", Path(tmp))
            self.assertTrue(ok)

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["outreach_status"], "Tertarik")
            self.assertEqual(saved[0]["outreach_notes"], "Tanya daftar harga")
            self.assertIsNone(saved[0].get("contacted_at"))

    def test_persist_status_unknown_entity_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            path.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")

            ok = persist_status_to_dossier("ent_9999", "Dihubungi", "Catatan", Path(tmp))
            self.assertFalse(ok)

    def test_persist_status_without_dossier_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok = persist_status_to_dossier("ent_0002", "Dihubungi", "Catatan", Path(tmp))
            self.assertFalse(ok)


class TestUpdateStatusEndpoint(unittest.TestCase):

    def setUp(self):
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), DashboardHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _post(self, path, payload):
        body = json.dumps(payload).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res, data

    def test_update_status_sample_lead_success(self):
        res, body = self._post("/api/leads/update-status", {
            "lead_id": "lead-001",
            "status": "Tertarik",
            "notes": "Minta dikirimi katalog sampel"
        })
        self.assertEqual(res.status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["persisted"])
        self.assertEqual(data["lead"]["outreach_status"], "Tertarik")
        self.assertEqual(data["lead"]["outreach_notes"], "Minta dikirimi katalog sampel")

    def test_update_status_dossier_lead_success_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "unified_dossiers_Makassar_20261025_000000.json"
            fixture.write_text(json.dumps([MULTI_CHANNEL_ENTITY], ensure_ascii=False), encoding="utf-8")

            with patch("scrapers.dashboard_server.find_latest_dossier", return_value=fixture):
                res, body = self._post("/api/leads/update-status", {
                    "lead_id": "ent_0002",
                    "status": "Dihubungi",
                    "notes": "Kontak via WhatsApp jam 10 pagi"
                })

            self.assertEqual(res.status, 200)
            data = json.loads(body)
            self.assertEqual(data["status"], "success")
            self.assertTrue(data["persisted"])
            self.assertEqual(data["lead"]["outreach_status"], "Dihubungi")
            self.assertEqual(data["lead"]["outreach_notes"], "Kontak via WhatsApp jam 10 pagi")

            # Verifikasi persistensi file fisik
            saved = json.loads(fixture.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["outreach_status"], "Dihubungi")
            self.assertEqual(saved[0]["outreach_notes"], "Kontak via WhatsApp jam 10 pagi")
            self.assertIsNotNone(saved[0].get("contacted_at"))

    def test_update_status_invalid_status_returns_400(self):
        res, body = self._post("/api/leads/update-status", {
            "lead_id": "lead-001",
            "status": "StatusTidakDikenal"
        })
        self.assertEqual(res.status, 400)
        data = json.loads(body)
        self.assertIn("error", data)
        self.assertIn("Status tidak valid", data["error"])

    def test_update_status_missing_fields_returns_400(self):
        res, body = self._post("/api/leads/update-status", {
            "lead_id": "lead-001"
        })
        self.assertEqual(res.status, 400)
        data = json.loads(body)
        self.assertIn("error", data)

    def test_update_status_unknown_lead_returns_404(self):
        with patch("scrapers.dashboard_server.find_latest_dossier", return_value=None):
            res, body = self._post("/api/leads/update-status", {
                "lead_id": "lead-tidak-ada-sama-sekali",
                "status": "Dihubungi"
            })
        self.assertEqual(res.status, 404)
        data = json.loads(body)
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
