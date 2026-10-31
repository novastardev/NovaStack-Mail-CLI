import unittest
from unittest.mock import Mock

from novastackmail.client import NovaStackMailClient, NovaStackMailError


class MailboxStatusApiTests(unittest.TestCase):
    def test_get_mailbox_uses_auth_me_and_returns_mailbox_profile(self):
        client = NovaStackMailClient(api_base="https://api.example.test")
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "success": True,
            "data": {"mailbox": {
                "id": "mailbox-123",
                "address": "nova@novastack.v6.rocks",
                "createdAt": "2026-10-01T12:00:00.000Z",
                "persistent": True,
            }},
        }
        client.session.get = Mock(return_value=response)

        mailbox = client.get_mailbox("a" * 43)

        self.assertEqual(mailbox["address"], "nova@novastack.v6.rocks")
        client.session.get.assert_called_once_with(
            "https://api.example.test/v1/mails/auth/me",
            headers={"Accept": "application/json", "Authorization": "Bearer " + "a" * 43},
            timeout=15,
        )

    def test_get_mailbox_rejects_expired_or_invalid_session(self):
        client = NovaStackMailClient()
        response = Mock()
        response.ok = False
        response.status_code = 401
        response.json.return_value = {
            "success": False,
            "message": "Mailbox access token is invalid or expired.",
        }
        client.session.get = Mock(return_value=response)

        with self.assertRaisesRegex(NovaStackMailError, "invalid or expired"):
            client.get_mailbox("a" * 43)

    def test_get_mailbox_rejects_malformed_token_before_request(self):
        client = NovaStackMailClient()
        client.session.get = Mock()

        with self.assertRaisesRegex(NovaStackMailError, "valid mailbox access token"):
            client.get_mailbox("bad")

        client.session.get.assert_not_called()
