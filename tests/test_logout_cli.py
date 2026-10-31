import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from novastackmail.config import load_config, save_config
from novastackmail.cli import main


class LogoutCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.env = patch.dict(os.environ, {"NOVASTACKMAIL_CONFIG": str(self.config_path)})
        self.env.start()
        save_config({
            "api_base": "https://api.example.test",
            "access_token": "a" * 43,
            "expires_at": "2026-11-29T14:00:00Z",
            "mailbox": {"address": "nova@novastack.v6.rocks"},
        })

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    @patch("novastackmail.cli.Confirm.ask", return_value=False)
    @patch("novastackmail.cli.NovaStackMailClient")
    def test_declining_confirmation_keeps_session(self, client_class, confirm):
        with patch("sys.argv", ["novastackmail", "--logout"]):
            self.assertEqual(main(), 0)

        client_class.assert_not_called()
        self.assertEqual(load_config(self.config_path)["access_token"], "a" * 43)

    @patch("novastackmail.cli.Confirm.ask", return_value=True)
    @patch("novastackmail.cli.NovaStackMailClient")
    def test_confirmed_logout_revokes_token_and_clears_local_config(self, client_class, confirm):
        client = Mock()
        client.logout.return_value = {"revoked": True}
        client_class.return_value = client

        with patch("sys.argv", ["novastackmail", "--logout"]):
            self.assertEqual(main(), 0)

        client.logout.assert_called_once_with("a" * 43)
        self.assertIsNone(load_config(self.config_path))

    @patch("novastackmail.cli.Confirm.ask", return_value=True)
    @patch("novastackmail.cli.NovaStackMailClient")
    def test_failed_remote_logout_keeps_local_credentials(self, client_class, confirm):
        from novastackmail.client import NovaStackMailError

        client = Mock()
        client.logout.side_effect = NovaStackMailError("Server unavailable.")
        client_class.return_value = client

        with patch("sys.argv", ["novastackmail", "--logout"]):
            self.assertEqual(main(), 1)

        self.assertEqual(load_config(self.config_path)["access_token"], "a" * 43)


if __name__ == "__main__":
    unittest.main()
