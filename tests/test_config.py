import os
import tempfile
import unittest
from pathlib import Path

from novastackmail.config import active_profile, load_config, save_config, clear_config, validate_profile_name


class ConfigTests(unittest.TestCase):
    def test_legacy_single_session_migrates_to_default_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"access_token":"test-token","expires_at":"later","mailbox":{"address":"one@example.test"}}', encoding="utf-8")
            config = load_config(path)
            self.assertEqual(config["active_profile"], "default")
            self.assertEqual(active_profile(config)["access_token"], "test-token")
            self.assertEqual(active_profile(config)["mailbox"]["address"], "one@example.test")
            self.assertNotIn("access_token", config)

    def test_multiple_profiles_and_active_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config({"profiles": {
                "personal": {"access_token": "a" * 43, "mailbox": {"address": "one@example.test"}},
                "school": {"access_token": "b" * 43, "mailbox": {"address": "two@example.test"}},
            }, "active_profile": "school"}, path)
            config = load_config(path)
            self.assertEqual(config["active_profile"], "school")
            self.assertEqual(active_profile(config)["mailbox"]["address"], "two@example.test")

    def test_profile_name_validation(self):
        self.assertTrue(validate_profile_name("mail_2"))
        self.assertFalse(validate_profile_name("../unsafe"))
        self.assertFalse(validate_profile_name(""))

    def test_config_file_permissions_are_private(self):
        if os.name == "nt":
            self.skipTest("POSIX permissions are unavailable")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config({"profiles": {"default": {"access_token": "secret"}}, "active_profile": "default"}, path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_clear_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config({"profiles": {}, "active_profile": None}, path)
            clear_config(path)
            self.assertIsNone(load_config(path))


if __name__ == "__main__":
    unittest.main()
