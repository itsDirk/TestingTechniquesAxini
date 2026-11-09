import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen
from uuid import uuid4


class MatrixConnectionError(RuntimeError):
    """Raised when a Matrix Client-Server API request fails."""


class MatrixConnection:
    """Small authenticated HTTP client for the Matrix Client-Server API."""

    def __init__(self, homeserver_url: str, access_token: str, timeout: float = 30):
        if not homeserver_url:
            raise ValueError('homeserver_url must not be empty')
        if not access_token:
            raise ValueError('access_token must not be empty')
        if not homeserver_url.startswith(('http://', 'https://')):
            raise ValueError('homeserver_url must use http:// or https://')

        self.homeserver_url = homeserver_url.rstrip('/') + '/'
        self.access_token = access_token
        self.timeout = timeout

    def create_room(self, name: str) -> dict:
        """Create a Matrix room and return the homeserver response."""
        if not name:
            raise ValueError('room name must not be empty')

        return self._request(
            'POST',
            '_matrix/client/v3/createRoom',
            {'name': name},
        )

    def whoami(self) -> dict:
        """Validate the access token and return the authenticated Matrix user."""
        return self._request('GET', '_matrix/client/v3/account/whoami')

    def send_text(self, room_id: str, body: str) -> dict:
        """Send an m.text room event and return the homeserver response."""
        if not room_id:
            raise ValueError('room_id must not be empty')

        transaction_id = uuid4().hex
        encoded_room_id = quote(room_id, safe='!:')
        encoded_transaction_id = quote(transaction_id, safe='')
        event_path = (
            f'_matrix/client/v3/rooms/{encoded_room_id}/send/'
            f'm.room.message/{encoded_transaction_id}'
        )

        return self._request(
            'PUT',
            event_path,
            {'msgtype': 'm.text', 'body': body},
        )

    def _request(self, method: str, path: str, payload: dict = None) -> dict:
        url = urljoin(self.homeserver_url, path)
        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = Request(
            url,
            data=body,
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json',
            },
            method=method,
        )
        if body is not None:
            request.add_header('Content-Type', 'application/json')

        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
        except HTTPError as error:
            response_body = error.read()
            detail = self._error_detail(response_body)
            raise MatrixConnectionError(
                f'Matrix API returned HTTP {error.code}: {detail}'
            ) from error
        except URLError as error:
            logging.error('Could not reach Matrix homeserver: %s', error.reason)
            raise MatrixConnectionError(
                f'Could not reach Matrix homeserver: {error.reason}'
            ) from error

        try:
            result = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise MatrixConnectionError(
                'Matrix API returned a response that was not valid JSON'
            ) from error

        if not isinstance(result, dict):
            raise MatrixConnectionError('Matrix API response must be a JSON object')
        return result

    @staticmethod
    def _error_detail(response_body: bytes) -> str:
        try:
            error = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return response_body.decode('utf-8', errors='replace') or 'no response body'

        if isinstance(error, dict):
            errcode = error.get('errcode')
            message = error.get('error')
            if errcode and message:
                return f'{errcode}: {message}'
            if message:
                return str(message)
        return 'unspecified Matrix API error'
