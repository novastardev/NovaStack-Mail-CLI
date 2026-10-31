import unittest
from io import StringIO

from rich.console import Console

from novastackmail.ui import (
    render_header,
    render_login_success,
    render_logout_cancelled,
    render_logout_success,
    render_status,
)


class TerminalUiTests(unittest.TestCase):
    def make_console(self):
        output = StringIO()
        return Console(file=output, force_terminal=False, color_system=None), output

    def test_header_contains_product_name_and_tagline(self):
        console, output = self.make_console()
        render_header(console)
        self.assertIn("NOVASTACK MAIL", output.getvalue())
        self.assertIn("Your mailbox. Your command line.", output.getvalue())

    def test_login_success_shows_mailbox_and_expiry(self):
        console, output = self.make_console()
        render_login_success(console, "nova@novastack.v6.rocks", "2026-11-29T13:50:24.369Z")
        rendered = output.getvalue()
        self.assertIn("nova@novastack.v6.rocks", rendered)
        self.assertIn("2026-11-29T13:50:24.369Z", rendered)
        self.assertIn("LOGIN SUCCESSFUL", rendered)

    def test_logout_success_shows_revoked_session(self):
        console, output = self.make_console()
        render_logout_success(console, "nova@novastack.v6.rocks")
        rendered = output.getvalue()
        self.assertIn("LOGOUT SUCCESSFUL", rendered)
        self.assertIn("nova@novastack.v6.rocks", rendered)
        self.assertIn("REVOKED", rendered)

    def test_logout_cancelled_confirms_session_is_kept(self):
        console, output = self.make_console()
        render_logout_cancelled(console)
        self.assertIn("Your session is still active", output.getvalue())

    def test_status_shows_mailbox_session_and_expiry_without_token(self):
        console, output = self.make_console()
        render_status(
            console,
            mailbox={
                "id": "mailbox-123",
                "address": "nova@novastack.v6.rocks",
                "createdAt": "2026-10-01T12:00:00.000Z",
                "persistent": True,
            },
            expires_at="2026-11-29T14:00:00Z",
            api_base="https://api.example.test",
        )
        rendered = output.getvalue()
        self.assertIn("MAILBOX STATUS", rendered)
        self.assertIn("nova@novastack.v6.rocks", rendered)
        self.assertIn("mailbox-123", rendered)
        self.assertIn("ACTIVE", rendered)
        self.assertIn("2026-11-29T14:00:00Z", rendered)
        self.assertIn("https://api.example.test", rendered)
        self.assertNotIn("a" * 43, rendered)


if __name__ == "__main__":
    unittest.main()
