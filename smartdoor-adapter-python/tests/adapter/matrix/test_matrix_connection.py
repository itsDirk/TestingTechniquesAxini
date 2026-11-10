import json
from unittest.mock import Mock, patch

import pytest

from matrix.matrix_connection import MatrixConnection, MatrixConnectionError


def _response(body):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = json.dumps(body).encode('utf-8')
    return response


def test_whoami_uses_authenticated_matrix_request():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'user_id': '@tester:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        result = connection.whoami()

    request = urlopen.call_args.args[0]
    assert request.full_url == 'http://matrix.example.org/_matrix/client/v3/account/whoami'
    assert request.method == 'GET'
    assert request.data is None
    assert request.get_header('Authorization') == 'Bearer test-token'
    assert result == {'user_id': '@tester:example.org'}


def test_create_room_posts_name_and_returns_room_id():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'room_id': '!room:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org/', 'test-token')
        result = connection.create_room('Test room')

    request = urlopen.call_args.args[0]
    assert request.full_url == 'http://matrix.example.org/_matrix/client/v3/createRoom'
    assert request.method == 'POST'
    assert json.loads(request.data) == {'name': 'Test room'}
    assert result == {'room_id': '!room:example.org'}


def test_create_room_forwards_empty_name_to_matrix():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'room_id': '!room:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        connection.create_room('')

    request = urlopen.call_args.args[0]
    assert request.method == 'POST'
    assert json.loads(request.data) == {'name': ''}


def test_leave_room_posts_to_room_leave_endpoint():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        connection.leave_room('!room:example.org')

    request = urlopen.call_args.args[0]
    assert request.full_url.endswith('/rooms/%21room%3Aexample.org/leave')
    assert request.method == 'POST'
    assert json.loads(request.data) == {}


def test_leave_room_forwards_empty_room_id_to_matrix():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        connection.leave_room('')

    assert urlopen.called
    assert urlopen.call_args.args[0].method == 'POST'


def test_send_message_uses_text_event_endpoint():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'event_id': '$event:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        result = connection.send_message('!room:example.org', 'Hello Matrix')

    request = urlopen.call_args.args[0]
    assert '/send/m.room.message/' in request.full_url
    assert request.method == 'PUT'
    assert json.loads(request.data) == {'msgtype': 'm.text', 'body': 'Hello Matrix'}
    assert result == {'event_id': '$event:example.org'}


def test_redact_event_uses_supplied_transaction_id():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'event_id': '$redaction:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        result = connection.redact_event(
            '!room:example.org',
            '$event:example.org',
            'redaction-txn',
        )

    request = urlopen.call_args.args[0]
    assert request.full_url.endswith(
        '/rooms/%21room%3Aexample.org/redact/%24event%3Aexample.org/redaction-txn'
    )
    assert request.method == 'PUT'
    assert json.loads(request.data) == {}
    assert result == {'event_id': '$redaction:example.org'}


def test_redact_event_forwards_empty_ids_to_matrix():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'errcode': 'M_UNRECOGNIZED'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        connection.redact_event('!room:example.org', '', '')

    request = urlopen.call_args.args[0]
    assert request.full_url.endswith('/rooms/%21room%3Aexample.org/redact/')
    assert request.method == 'PUT'


def test_replace_message_uses_matrix_edit_relation():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'event_id': '$edit:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        result = connection.replace_message(
            '!room:example.org',
            '$original:example.org',
            'Edited text',
        )

    request = urlopen.call_args.args[0]
    assert '/send/m.room.message/' in request.full_url
    assert request.method == 'PUT'
    assert json.loads(request.data) == {
        'msgtype': 'm.text',
        'body': '* Edited text',
        'm.new_content': {'msgtype': 'm.text', 'body': 'Edited text'},
        'm.relates_to': {
            'rel_type': 'm.replace',
            'event_id': '$original:example.org',
        },
    }
    assert result == {'event_id': '$edit:example.org'}


def test_pin_events_sets_pinned_events_state():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'event_id': '$pins:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        result = connection.pin_events(
            '!room:example.org',
            ['$first:example.org', '$second:example.org'],
        )

    request = urlopen.call_args.args[0]
    assert request.full_url.endswith(
        '/rooms/%21room%3Aexample.org/state/m.room.pinned_events/'
    )
    assert request.method == 'PUT'
    assert json.loads(request.data) == {
        'pinned': ['$first:example.org', '$second:example.org'],
    }
    assert result == {'event_id': '$pins:example.org'}


def test_reply_message_includes_in_reply_to_relation():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'event_id': '$reply:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        result = connection.reply_message(
            '!room:example.org',
            '$original:example.org',
            'A reply',
        )

    request = urlopen.call_args.args[0]
    assert '/send/m.room.message/' in request.full_url
    assert json.loads(request.data) == {
        'msgtype': 'm.text',
        'body': 'A reply',
        'm.relates_to': {'m.in_reply_to': {'event_id': '$original:example.org'}},
    }
    assert result == {'event_id': '$reply:example.org'}


def test_react_message_sends_annotation_relation():
    with patch(
        'matrix.matrix_connection.urlopen',
        return_value=_response({'event_id': '$reaction:example.org'}),
    ) as urlopen:
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        result = connection.react_message(
            '!room:example.org',
            '$original:example.org',
            '👍',
        )

    request = urlopen.call_args.args[0]
    assert '/send/m.reaction/' in request.full_url
    assert json.loads(request.data) == {
        'm.relates_to': {
            'rel_type': 'm.annotation',
            'event_id': '$original:example.org',
            'key': '👍',
        },
    }
    assert result == {'event_id': '$reaction:example.org'}


def test_matrix_api_errors_keep_http_and_matrix_error_codes():
    from io import BytesIO
    from urllib.error import HTTPError

    error = HTTPError(
        'http://matrix.example.org/_matrix/client/v3/createRoom',
        403,
        'Forbidden',
        {},
        BytesIO(b'{"errcode":"M_FORBIDDEN","error":"Not allowed"}'),
    )

    with patch('matrix.matrix_connection.urlopen', side_effect=error):
        connection = MatrixConnection('http://matrix.example.org', 'test-token')
        with pytest.raises(MatrixConnectionError, match='Not allowed') as raised:
            connection.create_room('Test room')

    assert raised.value.status_code == 403
    assert raised.value.errcode == 'M_FORBIDDEN'
