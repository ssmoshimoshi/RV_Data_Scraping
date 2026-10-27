import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

from scrapers.content_inspector import (
    clean_social_handle,
    detect_packaging_signals,
    calculate_engagement_metrics,
    evaluate_commercial_velocity,
    generate_content_pitch_hook,
    fetch_social_top_posts,
    save_inspected_posts_to_sqlite,
    load_cached_posts
)
from scrapers.db_sqlite import DDL_SCHEMA


class TestContentInspector(unittest.TestCase):

    def test_clean_social_handle(self):
        self.assertEqual(clean_social_handle("@titiktemumks"), "titiktemumks")
        self.assertEqual(clean_social_handle("titiktemumks"), "titiktemumks")
        self.assertEqual(clean_social_handle("https://instagram.com/titiktemumks/"), "titiktemumks")
        self.assertEqual(clean_social_handle("https://www.tiktok.com/@titiktemumks?is_copy_url=1"), "titiktemumks")
        self.assertEqual(clean_social_handle("  @Kedai.Kopi_Mks  "), "kedai.kopi_mks")
        self.assertEqual(clean_social_handle(""), "")

    def test_detect_packaging_signals_beverage(self):
        caption = "Menu baru es kopi susu dingin kami kini disajikan dalam Cold Cup 16oz dan Cup Sleeve Kraft tebal."
        res = detect_packaging_signals(caption, "fnb_beverage")
        self.assertTrue(res["has_signal"])
        self.assertIn("cold cup", res["detected_keywords"])
        self.assertTrue(any("Cup Sleeve" in prod for prod in res["recommended_products"]))

    def test_detect_packaging_signals_food(self):
        caption = "Pesanan paket bento lunch box dengan stiker segel khusus anti tumpah siap diantar."
        res = detect_packaging_signals(caption, "fnb_food_resto")
        self.assertTrue(res["has_signal"])
        self.assertTrue(any("Lunch Box" in prod or "Food Box" in prod for prod in res["recommended_products"]))

    def test_detect_packaging_signals_none(self):
        caption = "Selamat pagi warga Makassar, selamat beraktivitas dan semoga hari Anda menyenangkan."
        res = detect_packaging_signals(caption, "fnb_beverage")
        self.assertFalse(res["has_signal"])
        self.assertEqual(len(res["detected_keywords"]), 0)
        self.assertEqual(len(res["recommended_products"]), 0)

    def test_calculate_engagement_metrics_with_views(self):
        posts = [
            {"views": 10000, "likes": 500, "comments": 50},
            {"views": 20000, "likes": 1200, "comments": 80}
        ]
        res = calculate_engagement_metrics(posts, followers_count=5000)
        self.assertEqual(res["total_views"], 30000)
        self.assertEqual(res["total_likes"], 1700)
        self.assertEqual(res["total_comments"], 130)
        self.assertAlmostEqual(res["posts"][0]["engagement_rate"], 5.5, places=1)
        self.assertAlmostEqual(res["posts"][1]["engagement_rate"], 6.4, places=1)
        self.assertAlmostEqual(res["avg_engagement_rate"], 5.95, places=2)
        self.assertEqual(res["er_benchmark_status"], "Viral / High Traction")

    def test_calculate_engagement_metrics_with_followers(self):
        posts = [
            {"views": 0, "likes": 150, "comments": 15}
        ]
        res = calculate_engagement_metrics(posts, followers_count=10000)
        self.assertAlmostEqual(res["posts"][0]["engagement_rate"], 1.65, places=2)
        self.assertEqual(res["er_benchmark_status"], "Healthy Engagement")

    def test_calculate_engagement_metrics_empty(self):
        res = calculate_engagement_metrics([])
        self.assertEqual(res["total_views"], 0)
        self.assertEqual(res["avg_engagement_rate"], 0.0)
        self.assertEqual(res["er_benchmark_status"], "Belum Terukur")

    def test_evaluate_commercial_velocity(self):
        now = datetime.now()
        posts_high = [
            {"date": (now - timedelta(days=2)).strftime("%Y-%m-%d"), "packaging_signal": True},
            {"date": (now - timedelta(days=4)).strftime("%Y-%m-%d"), "packaging_signal": False},
            {"date": (now - timedelta(days=6)).strftime("%Y-%m-%d"), "packaging_signal": True},
            {"date": (now - timedelta(days=7)).strftime("%Y-%m-%d"), "packaging_signal": False}
        ]
        self.assertEqual(evaluate_commercial_velocity(posts_high, 4.5), "Tinggi")

        posts_moderate = [
            {"date": (now - timedelta(days=12)).strftime("%Y-%m-%d"), "packaging_signal": False},
            {"date": (now - timedelta(days=15)).strftime("%Y-%m-%d"), "packaging_signal": False}
        ]
        self.assertEqual(evaluate_commercial_velocity(posts_moderate, 1.8), "Moderat")

        posts_low = [
            {"date": (now - timedelta(days=28)).strftime("%Y-%m-%d"), "packaging_signal": False}
        ]
        self.assertEqual(evaluate_commercial_velocity(posts_low, 0.8), "Rendah")

        posts_inactive = [
            {"date": (now - timedelta(days=50)).strftime("%Y-%m-%d"), "packaging_signal": False}
        ]
        self.assertEqual(evaluate_commercial_velocity(posts_inactive, 0.0), "Tidak Terdeteksi")

    def test_generate_content_pitch_hook(self):
        top_post = {
            "caption": "Menu baru cold brew botol 250ml kami kini siap dipesan.",
            "views": 15400
        }
        needs = ["Botol Cold Brew PET Tebal", "Stiker Label Botol Vinyl"]
        res = generate_content_pitch_hook("Kopi Titik Temu", top_post, needs, "fnb_beverage", "081234567890")

        self.assertIn("Kopi Titik Temu", res["pitch_text"])
        self.assertIn("15,400 views", res["pitch_text"])
        self.assertIn("RUANG VISUAL", res["pitch_text"])
        self.assertTrue(res["wa_link"].startswith("https://wa.me/6281234567890"))

    def test_fetch_social_top_posts_dry_run(self):
        result = fetch_social_top_posts(
            platform="instagram",
            handle_or_url="@titiktemumks",
            business_name="Titik Temu Coffee",
            limit=5,
            dry_run=True
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["handle"], "@titiktemumks")
        self.assertEqual(result["platform"], "instagram")
        self.assertEqual(len(result["posts"]), 5)
        self.assertGreater(result["total_views"], 0)
        self.assertIn("outreach_hook", result)
        self.assertTrue(result["outreach_hook"]["pitch_text"])

    def test_sqlite_persistence_and_cache(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite") as tmp:
            tmp_path = Path(tmp.name)
            conn = sqlite3.connect(str(tmp_path))
            cur = conn.cursor()
            for stmt in DDL_SCHEMA.split(";"):
                if stmt.strip():
                    cur.execute(stmt.strip())
            
            # Buat entitas awal
            cur.execute("""
                INSERT INTO entities (entity_id, business_name, target_sector, primary_service_pillar, whatsapp_number)
                VALUES ('ent_test', 'Test Merchant', 'fnb_beverage', 'Packaging & Box', '6281234567890')
            """)
            cur.execute("""
                INSERT INTO digital_footprints (entity_id, instagram_handle, instagram_followers)
                VALUES ('ent_test', 'testmerchant_mks', 12000)
            """)
            conn.commit()
            conn.close()

            # Simpan postingan
            posts = [
                {
                    "id": "post_t1",
                    "caption": "Menu baru dengan cup sleeve kraft ramah lingkungan.",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "views": 5000,
                    "likes": 200,
                    "comments": 20,
                    "engagement_rate": 4.4,
                    "tags": ["Minuman / Beverage Pack"]
                }
            ]
            saved = save_inspected_posts_to_sqlite("ent_test", "instagram", posts, db_path=tmp_path)
            self.assertEqual(saved, 1)

            # Ambil kembali dari cache
            cached = load_cached_posts("testmerchant_mks", "instagram", db_path=tmp_path, max_age_days=7)
            self.assertIsNotNone(cached)
            self.assertEqual(cached["handle"], "@testmerchant_mks")
            self.assertEqual(cached["business_name"], "Test Merchant")
            self.assertEqual(len(cached["posts"]), 1)
            self.assertTrue(cached["posts"][0]["packaging_signal"])


if __name__ == "__main__":
    unittest.main()
