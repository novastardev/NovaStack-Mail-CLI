import unittest
from io import StringIO

from rich.console import Console

from novastackmail.ui import render_inbox


class InboxUiTests(unittest.TestCase):
    def test_inbox_renders_message_rows_and_empty_state(self):
        output = StringIO()
        # Give the table enough room to render full sender addresses.
        console = Console(file=output, width=120, force_terminal=False, color_system=None)
        render_inbox(console, "nova@novastack.v6.rocks", [
            {"id": "msg-1", "from": "hello@example.com", "subject": "Welcome", "date": "2026-10-30T10:00:00Z", "isRead": False},
            {"id": "msg-2", "from": "team@example.com", "subject": "Update", "date": "2026-10-29T10:00:00Z", "isRead": True}
        ])
        rendered = output.getvalue()
        self.assertIn("INBOX", rendered)
        self.assertIn("nova@novastack.v6.rocks", rendered)
        self.assertIn("MESSAGE ID", rendered)
        self.assertIn("msg-1", rendered)
        self.assertIn("hello@example.com", rendered)
        self.assertIn("Welcome", rendered)
        self.assertIn("Unread", rendered)
        self.assertIn("Read", rendered)

        output = StringIO()
        console = Console(file=output, width=120, force_terminal=False, color_system=None)
        render_inbox(console, "nova@novastack.v6.rocks", [])
        self.assertIn("No messages yet", output.getvalue())


if __name__ == "__main__":
    unittest.main()
