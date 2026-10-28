import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scrapers import phone_queue


class TestPhoneQueue(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = Path(self.temp_dir.name) / "test_phone_queue.json"
        self.patcher = patch.object(phone_queue, "QUEUE_FILE", self.temp_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_load_queue_creates_default_structure(self):
        data = phone_queue.load_queue()
        self.assertIn("queue", data)
        self.assertIn("updated_at", data)
        self.assertEqual(data["queue"], [])

    def test_add_to_queue_and_get_pending(self):
        item = phone_queue.add_to_queue("LD-0001", "Kopi Test", "instagram", "kopitest.id")
        self.assertEqual(item["lead_id"], "LD-0001")
        self.assertEqual(item["handle"], "kopitest.id")
        self.assertEqual(item["status"], "pending")

        pending = phone_queue.get_pending_items()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["handle"], "kopitest.id")

    def test_add_duplicate_returns_existing_item(self):
        item1 = phone_queue.add_to_queue("LD-0001", "Kopi Test", "instagram", "kopitest.id")
        item2 = phone_queue.add_to_queue("LD-0001", "Kopi Test", "instagram", "@kopitest.id")
        self.assertEqual(item1["id"], item2["id"])

        pending = phone_queue.get_pending_items()
        self.assertEqual(len(pending), 1)

    def test_update_item_status(self):
        item = phone_queue.add_to_queue("LD-0002", "Resto Test", "instagram", "restotest")
        q_id = item["id"]

        phone_queue.update_item_status(q_id, "processing")
        pending = phone_queue.get_pending_items()
        self.assertEqual(len(pending), 0)

        phone_queue.update_item_status(q_id, "completed")
        data = phone_queue.load_queue()
        self.assertEqual(data["queue"][0]["status"], "completed")

    def test_clear_completed_items(self):
        item1 = phone_queue.add_to_queue("LD-0001", "Kopi Satu", "instagram", "kopisatu")
        item2 = phone_queue.add_to_queue("LD-0002", "Kopi Dua", "instagram", "kopidua")

        phone_queue.update_item_status(item1["id"], "completed")
        removed = phone_queue.clear_completed_items()
        self.assertEqual(removed, 1)

        data = phone_queue.load_queue()
        self.assertEqual(len(data["queue"]), 1)
        self.assertEqual(data["queue"][0]["handle"], "kopidua")


if __name__ == "__main__":
    unittest.main()
