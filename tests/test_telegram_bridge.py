import unittest
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import patch, MagicMock
from scrapers.telegram_bridge import (
    format_profile_report,
    get_system_status,
    get_db_summary,
    get_control_panel_markup,
    get_persistent_keyboard_markup,
    handle_incoming_command
)


class TestTelegramBridge(unittest.TestCase):

    def test_format_profile_report(self):
        sample_profile = {
            "username": "kopiteori",
            "full_name": "KOPITEORI INDONESIA",
            "business_category": "Coffee shop",
            "followers_count": 27700,
            "posts_count": 680,
            "following_count": 1679,
            "whatsapp_number": "6281234567890",
            "email": "info@kopiteori.id",
            "address": "Makassar",
            "website_url": "visit.kopiteori.id",
            "bio": "Specialty Coffee Roastery Makassar"
        }

        report = format_profile_report(sample_profile)
        self.assertIn("@kopiteori", report)
        self.assertIn("KOPITEORI INDONESIA", report)
        self.assertIn("6281234567890", report)
        self.assertIn("27,700", report)
        self.assertIn("data/leads.sqlite", report)

    def test_get_system_status(self):
        status = get_system_status()
        self.assertIn("Xiaomi Redmi Note 14 5G", status)
        self.assertIn("Terhubung", status)

    def test_get_db_summary(self):
        summary = get_db_summary()
        self.assertIn("RUANG VISUAL", summary)
        self.assertIn("Total Entitas Bisnis", summary)

    def test_markups(self):
        inline_kb = get_control_panel_markup()
        self.assertIn("inline_keyboard", inline_kb)
        reply_kb = get_persistent_keyboard_markup()
        self.assertIn("keyboard", reply_kb)

    @patch("scrapers.telegram_bridge.send_telegram_message")
    def test_handle_incoming_command_help(self, mock_send):
        handle_incoming_command("/help", "123456", 1)
        self.assertTrue(mock_send.called)
        sent_text = mock_send.call_args[0][1]
        self.assertIn("PANDUAN PERINTAH", sent_text)
        self.assertIn("/set_ig", sent_text)
        self.assertIn("/edit_lead", sent_text)
        self.assertIn("/drop_lead", sent_text)

    @patch("scrapers.telegram_bridge.send_telegram_message")
    @patch("scrapers.telegram_bridge.execute_scrape_batch")
    @patch("scrapers.telegram_bridge.link_instagram_to_lead", return_value=True)
    def test_handle_incoming_command_set_ig(self, mock_link, mock_scrape, mock_send):
        handle_incoming_command("/set_ig LD-0001 kopiteori", "123456", 1)
        mock_link.assert_called_once_with("LD-0001", "kopiteori")
        self.assertTrue(mock_send.called)
        sent_text = mock_send.call_args[0][1]
        self.assertIn("Berhasil menautkan", sent_text)
        mock_scrape.assert_called_once_with("123456", ["kopiteori"], reply_to_message_id=1)

    @patch("scrapers.telegram_bridge.send_telegram_message")
    @patch("scrapers.telegram_bridge.update_lead_field", return_value=True)
    def test_handle_incoming_command_edit_lead(self, mock_update, mock_send):
        handle_incoming_command("/edit_lead LD-0001 wa 62812345678", "123456", 1)
        mock_update.assert_called_once_with("LD-0001", "wa", "62812345678")
        self.assertTrue(mock_send.called)
        sent_text = mock_send.call_args[0][1]
        self.assertIn("Berhasil memperbarui", sent_text)

    @patch("scrapers.telegram_bridge.send_telegram_message")
    @patch("scrapers.telegram_bridge.drop_lead", return_value=True)
    def test_handle_incoming_command_drop_lead(self, mock_drop, mock_send):
        handle_incoming_command("/drop_lead LD-0001 bukan target pasar", "123456", 1)
        mock_drop.assert_called_once_with("LD-0001", "bukan target pasar")
        self.assertTrue(mock_send.called)
        sent_text = mock_send.call_args[0][1]
        self.assertIn("telah dibatalkan", sent_text)


if __name__ == "__main__":
    unittest.main()
