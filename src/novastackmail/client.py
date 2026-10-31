import requests
from urllib.parse import quote


DEFAULT_API_BASE = "https://api-novastack.vercel.app"


class NovaStackMailError(Exception):
    pass


def _validate_access_token(access_token):
    return (
        isinstance(access_token, str)
        and len(access_token) == 43
        and all(character.isascii() and (character.isalnum() or character in "_-") for character in access_token)
    )


class NovaStackMailClient:
    def __init__(self, api_base=DEFAULT_API_BASE, access_token=None, timeout=15):
        self.api_base = api_base.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout
        self.session = requests.Session()

    def _headers(self, token=None):
        value = token or self.access_token
        if not _validate_access_token(value):
            raise NovaStackMailError("A valid mailbox access token is required.")
        return {"Accept": "application/json", "Authorization": "Bearer " + value}

    def _request_json(self, method, path, token=None, **kwargs):
        try:
            request_method = getattr(self.session, method.lower())
            response = request_method(
                self.api_base + path, headers=self._headers(token),
                timeout=self.timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise NovaStackMailError("Could not connect to NovaStack. Check your internet connection.") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise NovaStackMailError("NovaStack returned an invalid response.") from exc
        if not response.ok or payload.get("success") is not True:
            message = payload.get("message") or ("Request failed (HTTP " + str(response.status_code) + ").")
            raise NovaStackMailError(message)
        return payload.get("data") or {}

    def login(self, address, password):
        try:
            response = self.session.post(
                self.api_base + "/v1/mails/auth/login",
                json={"address": address.strip().lower(), "password": password},
                headers={"Accept": "application/json"}, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise NovaStackMailError("Could not connect to NovaStack. Check your internet connection.") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise NovaStackMailError("NovaStack returned an invalid response.") from exc
        if not response.ok or payload.get("success") is not True:
            raise NovaStackMailError(payload.get("message") or ("Login failed (HTTP " + str(response.status_code) + ")."))
        data = payload.get("data") or {}
        token = data.get("accessToken")
        if not _validate_access_token(token):
            raise NovaStackMailError("The server did not return a valid mailbox access token.")
        self.access_token = token
        return data

    def get_mailbox(self, access_token=None):
        mailbox = self._request_json("GET", "/v1/mails/auth/me", access_token).get("mailbox")
        if not isinstance(mailbox, dict) or not mailbox.get("address"):
            raise NovaStackMailError("NovaStack returned an incomplete mailbox profile.")
        return mailbox

    def get_inbox_page(self, page=1, per_page=10, access_token=None):
        if page < 1 or per_page < 1 or per_page > 50:
            raise NovaStackMailError("Page must be positive and per-page must be between 1 and 50.")
        data = self._request_json(
            "GET", "/v1/mails/auth/inbox/messages?page=" + str(page) + "&per_page=" + str(per_page),
            access_token,
        )
        messages = data.get("messages")
        pagination = data.get("pagination") or {}
        if not isinstance(messages, list):
            raise NovaStackMailError("NovaStack returned an invalid inbox message list.")
        return {"messages": messages, "pagination": pagination}

    def list_messages(self, access_token=None, page=1, per_page=10):
        return self.get_inbox_page(page, per_page, access_token)["messages"]

    def read_message(self, message_id, access_token=None):
        if not message_id or len(str(message_id)) > 200:
            raise NovaStackMailError("A valid message ID is required.")
        return self._request_json("GET", "/v1/mails/auth/messages/" + quote(str(message_id), safe=""), access_token)

    def delete_message(self, message_id, access_token=None):
        if not message_id or len(str(message_id)) > 200:
            raise NovaStackMailError("A valid message ID is required.")
        return self._request_json("DELETE", "/v1/mails/auth/messages/" + quote(str(message_id), safe=""), access_token)

    def download_attachment(self, message_id, attachment_id, access_token=None):
        if not message_id or not attachment_id:
            raise NovaStackMailError("A message ID and attachment ID are required.")
        path = "/v1/mails/auth/messages/" + quote(str(message_id), safe="") + "/attachments/" + quote(str(attachment_id), safe="")
        try:
            response = self.session.get(
                self.api_base + path, headers=self._headers(access_token), timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise NovaStackMailError("Could not connect to NovaStack. Check your internet connection.") from exc
        if not response.ok:
            try:
                payload = response.json()
                message = payload.get("message") or ("Attachment download failed (HTTP " + str(response.status_code) + ").")
            except ValueError:
                message = "Attachment download failed (HTTP " + str(response.status_code) + ")."
            raise NovaStackMailError(message)
        return response.content, response.headers.get("content-disposition", "")

    def logout(self, access_token):
        data = self._request_json("POST", "/v1/mails/auth/logout", access_token)
        if data.get("revoked") is not True:
            raise NovaStackMailError("NovaStack did not confirm that the session was revoked.")
        return data
