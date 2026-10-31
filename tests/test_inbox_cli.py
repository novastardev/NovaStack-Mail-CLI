import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from novastackmail.cli import main
from novastackmail.config import save_config
from novastackmail.client import NovaStackMailError


class InboxCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.env = patch.dict(os.environ, {"NOVASTACKMAIL_CONFIG": str(self.config_path)})
        self.env.start()
        save_config({"api_base": "https://api.example.test", "access_token": "a" * 43,
                     "mailbox": {"address": "nova@novastack.v6.rocks"}})

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    @patch("novastackmail.cli.NovaStackMailClient")
    def test_inbox_uses_page_size_and_displays_unread_messages(self, client_class):
        client = Mock()
        client.get_inbox_page.return_value = {
            "messages": [{"id": "msg-1", "from": "hello@example.com", "subject": "Welcome",
                          "date": "2026-10-30T10:00:00Z", "isRead": False}],
            "pagination": {"page": 2, "perPage": 10, "total": 12, "totalPages": 2},
        }
        client_class.return_value = client
        with patch("sys.argv", ["novastackmail", "--inbox", "--page", "2", "--per-page", "10"]):
            self.assertEqual(main(), 0)
        client.get_inbox_page.assert_called_once_with(2, 10)

    @patch("novastackmail.cli.NovaStackMailClient")
    def test_read_message_calls_message_endpoint(self, client_class):
        client = Mock()
        client.read_message.return_value = {"id": "msg-1", "text": "Hello", "attachments": []}
        client_class.return_value = client
        with patch("sys.argv", ["novastackmail", "--read", "msg-1", "--quiet"]):
            self.assertEqual(main(), 0)
        client.read_message.assert_called_once_with("msg-1")

    @patch("novastackmail.cli.NovaStackMailClient")
    @patch("novastackmail.cli.Confirm.ask", return_value=True)
    def test_delete_requires_confirmation_and_calls_delete_endpoint(self, confirm, client_class):
        client = Mock()
        client.delete_message.return_value = {"id": "msg-1", "deleted": True}
        client_class.return_value = client
        with patch("sys.argv", ["novastackmail", "--delete", "msg-1"]):
            self.assertEqual(main(), 0)
        client.delete_message.assert_called_once_with("msg-1")

    @patch("novastackmail.cli.NovaStackMailClient")
    def test_inbox_api_error_is_reported(self, client_class):
        client = Mock()
        client.get_inbox_page.side_effect = NovaStackMailError("Inbox service unavailable.")
        client_class.return_value = client
        with patch("sys.argv", ["novastackmail", "--inbox"]):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
