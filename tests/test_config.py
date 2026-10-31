import os
import tempfile
import unittest
from pathlib import Path

from novastackmail.config import load_config, save_config, clear_config


class ConfigTests(unittest.TestCase):
    def test_save_and_load_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config({"access_token": "test-token"}, path)
            self.assertEqual(load_config(path)["access_token"], "test-token")

    def test_config_file_permissions_are_private(self):
        if os.name == "nt":
            self.skipTest("POSIX permissions are unavailable")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config({"access_token": "secret"}, path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_clear_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config({"access_token": "secret"}, path)
            clear_config(path)
            self.assertIsNone(load_config(path))


if __name__ == "__main__":
    unittest.main()
