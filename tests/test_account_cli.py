import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from novastackmail.cli import main
from novastackmail.config import active_profile, load_config, save_config


class AccountProfileCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.env = patch.dict(os.environ, {"NOVASTACKMAIL_CONFIG": str(self.config_path)}, clear=False)
        self.env.start()
        save_config({
            "profiles": {
                "personal": {
                    "api_base": "https://api.example.test",
                    "access_token": "a" * 43,
                    "mailbox": {"address": "personal@example.test"},
                },
                "school": {
                    "api_base": "https://api.example.test",
                    "access_token": "b" * 43,
                    "mailbox": {"address": "school@example.test"},
                },
            },
            "active_profile": "personal",
        }, self.config_path)

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def test_list_profiles_shows_addresses_and_active_profile_without_tokens(self):
        output = StringIO()
        with patch("sys.argv", ["novastackmail", "--json", "account", "list"]), redirect_stdout(output):
            self.assertEqual(main(), 0)

        result = json.loads(output.getvalue())
        self.assertEqual(result["activeProfile"], "personal")
        self.assertEqual({item["name"] for item in result["profiles"]}, {"personal", "school"})
        self.assertTrue(next(item for item in result["profiles"] if item["name"] == "personal")["active"])
        self.assertNotIn("access_token", output.getvalue())
        self.assertNotIn("aaaaaaaa", output.getvalue())

    def test_use_switches_active_profile(self):
        with patch("sys.argv", ["novastackmail", "account", "use", "school"]):
            self.assertEqual(main(), 0)

        self.assertEqual(load_config(self.config_path)["active_profile"], "school")

    @patch("novastackmail.cli.Confirm.ask", return_value=True)
    @patch("novastackmail.cli.NovaStackMailClient")
    def test_remove_revokes_only_selected_profile_and_keeps_other_profiles(self, client_class, confirm):
        client = Mock()
        client.logout.return_value = {"revoked": True}
        client_class.return_value = client

        with patch("sys.argv", ["novastackmail", "account", "remove", "school"]):
            self.assertEqual(main(), 0)

        client.logout.assert_called_once_with("b" * 43)
        config = load_config(self.config_path)
        self.assertEqual(set(config["profiles"]), {"personal"})
        self.assertEqual(config["active_profile"], "personal")

    @patch("novastackmail.cli.Prompt.ask", return_value="new@example.test")
    @patch("novastackmail.cli.getpass.getpass", return_value="mailbox-password")
    @patch("novastackmail.cli.NovaStackMailClient")
    def test_add_logs_in_and_saves_an_additional_profile(self, client_class, password, prompt):
        client = Mock()
        client.login.return_value = {
            "accessToken": "c" * 43,
            "expiresAt": "2026-12-01T00:00:00Z",
            "mailbox": {"address": "new@example.test"},
        }
        client_class.return_value = client

        with patch("sys.argv", ["novastackmail", "account", "add", "work"]):
            self.assertEqual(main(), 0)

        client.login.assert_called_once_with("new@example.test", "mailbox-password")
        config = load_config(self.config_path)
        self.assertEqual(config["active_profile"], "personal")
        self.assertEqual(config["profiles"]["work"]["access_token"], "c" * 43)
        self.assertEqual(config["profiles"]["work"]["mailbox"]["address"], "new@example.test")


if __name__ == "__main__":
    unittest.main()
