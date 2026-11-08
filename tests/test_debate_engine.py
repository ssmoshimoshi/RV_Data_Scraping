import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
import tempfile
from scrapers.db_sqlite import init_db
from scrapers.debate_engine import generate_debate_rounds, run_automated_debate


class TestDebateEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test_debate.sqlite'
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_debate_rounds_scraping(self):
        rounds = generate_debate_rounds("Scraping Instagram Profile via Playwright")
        self.assertIn("round_1", rounds)
        self.assertIn("round_2", rounds)
        self.assertIn("round_3", rounds)
        self.assertEqual(rounds["round_1"]["agent_name"], "Kilo")
        self.assertEqual(rounds["round_2"]["agent_name"], "Antigravity")
        self.assertIn("Dieliminasi", rounds["round_3"]["content"])

    def test_run_automated_debate_persists_to_db(self):
        res = run_automated_debate("Evaluasi Caching Redis vs SQLite", db_path=self.db_path)
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "concluded")
        self.assertEqual(len(res["turns"]), 3)
        self.assertEqual(res["turns"][0]["agent_name"], "Kilo")
        self.assertEqual(res["turns"][1]["agent_name"], "Antigravity")
        self.assertEqual(res["turns"][2]["agent_name"], "Konsensus Multi-Agen")


if __name__ == '__main__':
    unittest.main()
