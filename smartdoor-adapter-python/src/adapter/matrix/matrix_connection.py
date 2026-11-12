import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen
from uuid import uuid4


class MatrixConnectionError(RuntimeError):
    """Raised when a Matrix Client-Server API request fails."""

    def __init__(self, message: str, status_code: int = None, errcode: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.errcode = errcode


class MatrixConnection:
    """Authenticated HTTP client for the Matrix Client-Server API."""

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

    def whoami(self) -> dict:
        """Validate the access token and return the authenticated Matrix user."""
        return self._request('GET', '_matrix/client/v3/account/whoami')

    def create_room(self, name: str) -> dict:
        """Create a room and return its Matrix room ID."""
        return self._request('POST', '_matrix/client/v3/createRoom', {'name': name})

    def leave_room(self, room_id: str) -> dict:
        """Leave a room as the user authenticated by this connection."""
        return self._request(
            'POST',
            f'_matrix/client/v3/rooms/{self._path_id(room_id)}/leave',
            {},
        )

    def send_message(self, room_id: str, message: str) -> dict:
        """Send an m.text event to a room."""
        return self.send_event(
            room_id,
            'm.room.message',
            {'msgtype': 'm.text', 'body': message},
        )

    def redact_event(self, room_id: str, event_id: str, transaction_id: str) -> dict:
        """Redact a room event using the supplied transaction ID."""
        path = (
            f'_matrix/client/v3/rooms/{self._path_id(room_id)}/redact/'
            f'{self._path_id(event_id)}/{quote(transaction_id, safe="")}'
        )
        return self._request('PUT', path, {})

    def replace_message(self, room_id: str, event_id: str, message: str) -> dict:
        """Send an m.replace edit event for a previous room message."""
        content = {
            'msgtype': 'm.text',
            'body': f'* {message}',
            'm.new_content': {'msgtype': 'm.text', 'body': message},
            'm.relates_to': {'rel_type': 'm.replace', 'event_id': event_id},
        }
        return self.send_event(room_id, 'm.room.message', content)

    def pin_events(self, room_id: str, event_ids: list[str]) -> dict:
        """Set a room's pinned-event state to the provided list of event IDs."""
        return self._request(
            'PUT',
            f'_matrix/client/v3/rooms/{self._path_id(room_id)}/state/'
            'm.room.pinned_events/',
            {'pinned': event_ids},
        )

    def reply_message(self, room_id: str, event_id: str, message: str) -> dict:
        """Send a text message linked as a reply to another event."""
        content = {
            'msgtype': 'm.text',
            'body': message,
            'm.relates_to': {'m.in_reply_to': {'event_id': event_id}},
        }
        return self.send_event(room_id, 'm.room.message', content)

    def react_message(self, room_id: str, event_id: str, reaction: str) -> dict:
        """Send an m.annotation reaction to a room event."""
        return self.send_event(
            room_id,
            'm.reaction',
            {
                'm.relates_to': {
                    'rel_type': 'm.annotation',
                    'event_id': event_id,
                    'key': reaction,
                },
            },
        )

    def send_event(self, room_id: str, event_type: str, content: dict) -> dict:
        """Send a room event of the specified Matrix event type."""
        transaction_id = quote(uuid4().hex, safe='')
        path = (
            f'_matrix/client/v3/rooms/{self._path_id(room_id)}/send/'
            f'{quote(event_type, safe="")}/{transaction_id}'
        )
        return self._request('PUT', path, content)

    @staticmethod
    def _path_id(value: str) -> str:
        return quote(value, safe='')

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
            errcode, detail = self._error_detail(response_body)
            raise MatrixConnectionError(
                f'Matrix API returned HTTP {error.code}: {detail}',
                status_code=error.code,
                errcode=errcode,
            ) from error
        except URLError as error:
            logging.error('Could not reach Matrix homeserver: %s', error.reason)
            raise MatrixConnectionError(
                f'Could not reach Matrix homeserver: {error.reason}',
                status_code=503,
                errcode='M_HOMESERVER_UNREACHABLE',
            ) from error

        if not response_body:
            return {}

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
    def _error_detail(response_body: bytes) -> tuple[str, str]:
        try:
            error = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return '', response_body.decode('utf-8', errors='replace') or 'no response body'

        if isinstance(error, dict):
            errcode = error.get('errcode')
            message = error.get('error')
            if errcode and message:
                return str(errcode), str(message)
            if message:
                return '', str(message)
        return '', 'unspecified Matrix API error'
