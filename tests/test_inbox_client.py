import unittest
from unittest.mock import Mock

from novastackmail.client import NovaStackMailClient, NovaStackMailError


class MailboxInboxTests(unittest.TestCase):
    def test_list_messages_uses_saved_bearer_token_and_returns_messages(self):
        client = NovaStackMailClient(api_base="https://api.example.test", access_token="a" * 43)
        response = Mock()
        response.ok = True
        response.json.return_value = {"success": True, "data": {
            "messages": [{"id": "msg-1", "from": "hello@example.com", "subject": "Welcome", "date": "2026-10-30T10:00:00Z", "isRead": False}],
            "pagination": {"page": 1, "perPage": 10, "total": 1, "totalPages": 1},
        }}
        client.session.get = Mock(return_value=response)
        result = client.get_inbox_page(1, 10)
        self.assertEqual(result["messages"][0]["id"], "msg-1")
        self.assertFalse(result["messages"][0]["isRead"])
        client.session.get.assert_called_once_with(
            "https://api.example.test/v1/mails/auth/inbox/messages?page=1&per_page=10",
            headers={"Accept": "application/json", "Authorization": "Bearer " + "a" * 43}, timeout=15,
        )

    def test_inbox_rejects_invalid_pagination(self):
        client = NovaStackMailClient(access_token="a" * 43)
        client.session.get = Mock()
        with self.assertRaisesRegex(NovaStackMailError, "Page must be positive"):
            client.get_inbox_page(0, 10)
        client.session.get.assert_not_called()

    def test_list_messages_rejects_missing_token(self):
        client = NovaStackMailClient()
        client.session.get = Mock()
        with self.assertRaisesRegex(NovaStackMailError, "valid mailbox access token"):
            client.list_messages()
        client.session.get.assert_not_called()

    def test_read_message_returns_message_details(self):
        client = NovaStackMailClient(access_token="a" * 43)
        response = Mock()
        response.ok = True
        response.json.return_value = {"success": True, "data": {"id": "msg-1", "text": "Hello"}}
        client.session.get = Mock(return_value=response)
        self.assertEqual(client.read_message("msg-1")["text"], "Hello")
        client.session.get.assert_called_once_with(
            "https://api-novastack.vercel.app/v1/mails/auth/messages/msg-1",
            headers={"Accept": "application/json", "Authorization": "Bearer " + "a" * 43}, timeout=15,
        )

    def test_delete_message_uses_delete_request(self):
        client = NovaStackMailClient(access_token="a" * 43)
        response = Mock()
        response.ok = True
        response.json.return_value = {"success": True, "data": {"id": "msg-1", "deleted": True}}
        client.session.delete = Mock(return_value=response)
        self.assertTrue(client.delete_message("msg-1")["deleted"])
        client.session.delete.assert_called_once()

    def test_download_attachment_returns_bytes_and_filename_header(self):
        client = NovaStackMailClient(access_token="a" * 43)
        response = Mock()
        response.ok = True
        response.content = b"file-data"
        response.headers = {"content-disposition": 'attachment; filename="report.pdf"'}
        client.session.get = Mock(return_value=response)
        content, disposition = client.download_attachment("msg-1", "att-1")
        self.assertEqual(content, b"file-data")
        self.assertIn("report.pdf", disposition)

    def test_server_errors_are_reported(self):
        client = NovaStackMailClient(access_token="a" * 43)
        response = Mock()
        response.ok = False
        response.status_code = 401
        response.json.return_value = {"success": False, "message": "Mailbox access token is invalid or expired."}
        client.session.get = Mock(return_value=response)
        with self.assertRaisesRegex(NovaStackMailError, "invalid or expired"):
            client.get_inbox_page()


if __name__ == "__main__":
    unittest.main()
