import unittest
from unittest.mock import Mock

from novastackmail.client import NovaStackMailClient, NovaStackMailError


class MailboxReadStatusTests(unittest.TestCase):
    def test_set_message_read_sends_boolean_patch(self):
        client = NovaStackMailClient(api_base="https://api.example.test")
        response = Mock()
        response.ok = True
        response.json.return_value = {"success": True, "data": {"id": "msg-1", "isRead": True}}
        client.session.patch = Mock(return_value=response)

        result = client.set_message_read("msg-1", True, "a" * 43)

        self.assertTrue(result["isRead"])
        client.session.patch.assert_called_once_with(
            "https://api.example.test/v1/mails/auth/messages/msg-1/read",
            headers={"Accept": "application/json", "Authorization": "Bearer " + "a" * 43},
            timeout=15,
            json={"isRead": True},
        )

    def test_set_message_read_rejects_non_boolean(self):
        client = NovaStackMailClient()
        client.session.patch = Mock()
        with self.assertRaisesRegex(NovaStackMailError, "must be true or false"):
            client.set_message_read("msg-1", "true", "a" * 43)
        client.session.patch.assert_not_called()


class MailboxLogoutTests(unittest.TestCase):
    def test_logout_revokes_token_with_bearer_authorization(self):
        client = NovaStackMailClient(api_base="https://api.example.test")
        response = Mock()
        response.ok = True
        response.json.return_value = {"success": True, "data": {"revoked": True}}
        client.session.post = Mock(return_value=response)

        result = client.logout("a" * 43)

        self.assertTrue(result["revoked"])
        client.session.post.assert_called_once_with(
            "https://api.example.test/v1/mails/auth/logout",
            headers={"Accept": "application/json", "Authorization": "Bearer " + "a" * 43},
            timeout=15,
        )

    def test_logout_rejects_unsuccessful_server_response(self):
        client = NovaStackMailClient()
        response = Mock()
        response.ok = False
        response.status_code = 503
        response.json.return_value = {
            "success": False,
            "message": "Logout service unavailable.",
        }
        client.session.post = Mock(return_value=response)

        with self.assertRaisesRegex(NovaStackMailError, "Logout service unavailable"):
            client.logout("a" * 43)

    def test_logout_rejects_malformed_token_before_request(self):
        client = NovaStackMailClient()
        client.session.post = Mock()

        with self.assertRaisesRegex(NovaStackMailError, "valid mailbox access token"):
            client.logout("invalid")

        client.session.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
