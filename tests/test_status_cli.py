import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from novastackmail.cli import main
from novastackmail.config import load_config, save_config
from novastackmail.client import NovaStackMailError


class StatusCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.env = patch.dict(os.environ, {"NOVASTACKMAIL_CONFIG": str(self.config_path)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def test_status_without_saved_session_returns_not_signed_in(self):
        with patch("sys.argv", ["novastackmail", "--status"]):
            self.assertEqual(main(), 0)

    @patch("novastackmail.cli.NovaStackMailClient")
    def test_status_displays_live_mailbox_profile(self, client_class):
        save_config({
            "api_base": "https://api.example.test",
            "access_token": "a" * 43,
            "expires_at": "2026-11-29T14:00:00Z",
            "mailbox": {"address": "cached@novastack.v6.rocks"},
        })
        client = Mock()
        client.get_mailbox.return_value = {
            "id": "mailbox-123",
            "address": "nova@novastack.v6.rocks",
            "createdAt": "2026-10-01T12:00:00.000Z",
            "persistent": True,
        }
        client_class.return_value = client

        with patch("sys.argv", ["novastackmail", "--status"]):
            self.assertEqual(main(), 0)

        client.get_mailbox.assert_called_once_with("a" * 43)

    @patch("novastackmail.cli.NovaStackMailClient")
    def test_status_reports_expired_session_without_deleting_saved_token(self, client_class):
        save_config({
            "api_base": "https://api.example.test",
            "access_token": "a" * 43,
            "mailbox": {"address": "nova@novastack.v6.rocks"},
        })
        client = Mock()
        client.get_mailbox.side_effect = NovaStackMailError(
            "Mailbox access token is invalid or expired."
        )
        client_class.return_value = client

        with patch("sys.argv", ["novastackmail", "--status"]):
            self.assertEqual(main(), 1)

        self.assertEqual(load_config(self.config_path)["access_token"], "a" * 43)


if __name__ == "__main__":
    unittest.main()
