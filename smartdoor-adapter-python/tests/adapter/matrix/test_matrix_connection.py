import json
from unittest.mock import Mock, patch

import pytest

from matrix.matrix_connection import MatrixConnection, MatrixConnectionError


def test_create_room_sends_authenticated_matrix_request():
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = b'{"room_id":"!room:example.org"}'

    with patch('matrix.matrix_connection.urlopen', return_value=response) as urlopen:
        connection = MatrixConnection('https://matrix.example.org', 'test-token')
        result = connection.create_room('Test room')

    request = urlopen.call_args.args[0]
    assert request.full_url == 'https://matrix.example.org/_matrix/client/v3/createRoom'
    assert request.method == 'POST'
    assert request.get_header('Authorization') == 'Bearer test-token'
    assert json.loads(request.data) == {'name': 'Test room'}
    assert result == {'room_id': '!room:example.org'}


def test_whoami_validates_access_token():
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = b'{"user_id":"@tester:example.org"}'

    with patch('matrix.matrix_connection.urlopen', return_value=response) as urlopen:
        connection = MatrixConnection('https://matrix.example.org', 'test-token')
        result = connection.whoami()

    request = urlopen.call_args.args[0]
    assert request.full_url == 'https://matrix.example.org/_matrix/client/v3/account/whoami'
    assert request.method == 'GET'
    assert request.data is None
    assert request.get_header('Authorization') == 'Bearer test-token'
    assert result == {'user_id': '@tester:example.org'}


def test_send_text_encodes_room_id_and_sends_text_event():
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = b'{"event_id":"$event:example.org"}'

    with patch('matrix.matrix_connection.urlopen', return_value=response) as urlopen:
        connection = MatrixConnection('https://matrix.example.org/', 'test-token')
        result = connection.send_text('!room:example.org', 'Hello Matrix')

    request = urlopen.call_args.args[0]
    assert '/rooms/!room:example.org/send/m.room.message/' in request.full_url
    assert request.method == 'PUT'
    assert json.loads(request.data) == {'msgtype': 'm.text', 'body': 'Hello Matrix'}
    assert result == {'event_id': '$event:example.org'}


def test_matrix_api_errors_include_matrix_error_details():
    from io import BytesIO
    from urllib.error import HTTPError

    error = HTTPError(
        'https://matrix.example.org/_matrix/client/v3/createRoom',
        403,
        'Forbidden',
        {},
        BytesIO(b'{"errcode":"M_FORBIDDEN","error":"Not allowed"}'),
    )

    with patch('matrix.matrix_connection.urlopen', side_effect=error):
        connection = MatrixConnection('https://matrix.example.org', 'test-token')
        with pytest.raises(MatrixConnectionError, match='M_FORBIDDEN: Not allowed'):
            connection.create_room('Test room')
