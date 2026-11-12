from unittest.mock import patch

from generic.api.label import Label, Sort
from generic.api import label_pb2
from generic.api.parameter import Parameter
from generic.api.type import Type
from matrix.handler import Handler, MATRIX_CHANNEL
from matrix.matrix_connection import MatrixConnectionError


class AdapterCoreStub:
    def __init__(self):
        self.confirmations = []
        self.responses = []
        self.ready_calls = 0

    def send_stimulus_confirmation(self, label):
        self.confirmations.append(label)

    def send_response(self, label):
        self.responses.append(label)

    def send_ready(self):
        self.ready_calls += 1


class MatrixConnectionStub:
    def whoami(self):
        return {'user_id': '@tester:example.org'}

    def create_room(self, name):
        assert name == 'Test room'
        return {'room_id': '!room:example.org'}

    def leave_room(self, room_id):
        if not room_id:
            raise MatrixConnectionError(
                'Matrix API returned HTTP 404: Unrecognized request',
                status_code=404,
                errcode='M_UNRECOGNIZED',
            )
        assert room_id == '!room:example.org'
        return {}

    def send_message(self, room_id, message):
        assert room_id == '!room:example.org'
        assert message == 'Hello Matrix'
        return {'event_id': '$message:example.org'}

    def redact_event(self, room_id, event_id, redaction_id):
        assert room_id == '!room:example.org'
        assert event_id == '$message:example.org'
        assert redaction_id == 'redact-txn'
        return {'event_id': '$redaction:example.org'}

    def replace_message(self, room_id, event_id, message):
        assert room_id == '!room:example.org'
        assert event_id == '$message:example.org'
        assert message == 'Edited message'
        return {'event_id': '$edit:example.org'}

    def pin_events(self, room_id, event_ids):
        assert room_id == '!room:example.org'
        assert event_ids == ['$message:example.org']
        return {'event_id': '$pins:example.org'}

    def reply_message(self, room_id, event_id, message):
        assert room_id == '!room:example.org'
        assert event_id == '$message:example.org'
        assert message == 'A reply'
        return {'event_id': '$reply:example.org'}

    def react_message(self, room_id, event_id, reaction):
        assert room_id == '!room:example.org'
        assert event_id == '$message:example.org'
        assert reaction == '👍'
        return {'event_id': '$reaction:example.org'}


def _stimulate(handler, name, parameters):
    encoded_parameters = []
    for parameter_name, value in parameters.items():
        if value is None:
            encoded_parameters.append(label_pb2.Label.Parameter(name=parameter_name))
            continue
        tipe = Type.ARRAY if isinstance(value, list) else Type.STRING
        encoded_parameters.append(Parameter(parameter_name, tipe, value))
    label = label_pb2.Label(
        type=label_pb2.Label.LabelType.STIMULUS,
        label=name,
        channel=MATRIX_CHANNEL,
        parameters=[
            parameter if isinstance(parameter, label_pb2.Label.Parameter) else parameter.encode()
            for parameter in encoded_parameters
        ],
    )
    handler.stimulate(label)


def _parameters(label):
    return {parameter.name: parameter.value for parameter in label.parameters}


def _handler():
    handler = Handler()
    handler.adapter_core = AdapterCoreStub()
    handler.sut = MatrixConnectionStub()
    handler.user_id = '@tester:example.org'
    return handler


def test_announced_labels_match_model_contract():
    labels = Handler().supported_labels()
    stimuli = [label for label in labels if label.sort == Sort.STIMULUS]

    assert {label.name for label in stimuli} == {
        'create_room',
        'leave_room',
        'send_message',
        'redact_event',
        'replace_message',
        'pin_event',
        'reply_event',
        'react_message',
    }
    assert all(label.channel == MATRIX_CHANNEL for label in labels)
    assert next(label for label in labels if label.name == 'succes').parameters[1].tipe == Type.STRING


def test_create_room_returns_matrix_room_id():
    handler = _handler()

    _stimulate(handler, 'create_room', {'name': 'Test room'})

    response = handler.adapter_core.responses[0]
    assert response.name == 'succes'
    assert _parameters(response) == {'code': 200, 'id': '!room:example.org'}


def test_leave_room_with_empty_room_id_forwards_matrix_error_even_if_user_differs():
    handler = _handler()

    _stimulate(handler, 'leave_room', {
        'room_id': '',
        'user_id': 'user',
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'error'
    assert _parameters(response) == {
        'code': 400,
        'error_msg': 'M_UNRECOGNIZED',
        'error_text': 'Matrix API returned HTTP 404: Unrecognized request',
    }


def test_leave_room_with_authenticated_user_succeeds():
    handler = _handler()

    _stimulate(handler, 'leave_room', {
        'room_id': '!room:example.org',
        'user_id': '@tester:example.org',
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'succes'
    assert _parameters(response) == {'code': 200, 'id': '!room:example.org'}


def test_leave_room_rejects_different_user_without_impersonating():
    handler = _handler()

    _stimulate(handler, 'leave_room', {
        'room_id': '!room:example.org',
        'user_id': '@someone-else:example.org',
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'error'
    assert _parameters(response)['code'] == 403
    assert _parameters(response)['error_msg'] == 'M_FORBIDDEN'
    assert 'access token belongs to @tester:example.org' in _parameters(response)['error_text']


def test_send_message_returns_matrix_event_id():
    handler = _handler()

    _stimulate(handler, 'send_message', {
        'message': 'Hello Matrix',
        'room_id': '!room:example.org',
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'succes'
    assert _parameters(response) == {'code': 200, 'id': '$message:example.org'}


def test_redact_event_returns_redaction_event_id():
    handler = _handler()

    _stimulate(handler, 'redact_event', {
        'event_id': '$message:example.org',
        'room_id': '!room:example.org',
        'redaction_id': 'redact-txn',
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'succes'
    assert _parameters(response) == {'code': 200, 'id': '$redaction:example.org'}


def test_void_redaction_id_returns_missing_parameter_error_without_calling_matrix():
    class RejectingConnection(MatrixConnectionStub):
        def redact_event(self, room_id, event_id, redaction_id):
            raise AssertionError('Matrix must not be called with a void parameter')

    handler = _handler()
    handler.sut = RejectingConnection()

    _stimulate(handler, 'redact_event', {
        'event_id': '$message:example.org',
        'room_id': '!room:example.org',
        'redaction_id': None,
    })

    assert len(handler.adapter_core.confirmations) == 1
    response = handler.adapter_core.responses[0]
    assert response.name == 'error'
    assert _parameters(response) == {
        'code': 400,
        'error_msg': 'M_MISSING_PARAM',
        'error_text': 'Missing required Matrix stimulus parameter "redaction_id"',
    }


def test_replace_message_returns_new_edit_event_id():
    handler = _handler()

    _stimulate(handler, 'replace_message', {
        'message': 'Edited message',
        'room_id': '!room:example.org',
        'event_id': '$message:example.org',
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'succes'
    assert _parameters(response) == {'code': 200, 'id': '$edit:example.org'}


def test_pin_event_uses_model_event_id_list_parameter():
    handler = _handler()

    _stimulate(handler, 'pin_event', {
        'room_id': '!room:example.org',
        'event_id_list': ['$message:example.org'],
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'succes'
    assert _parameters(response) == {'code': 200, 'id': '$pins:example.org'}


def test_reply_event_returns_reply_event_id():
    handler = _handler()

    _stimulate(handler, 'reply_event', {
        'message': 'A reply',
        'room_id': '!room:example.org',
        'event_id': '$message:example.org',
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'succes'
    assert _parameters(response) == {'code': 200, 'id': '$reply:example.org'}


def test_react_message_returns_reaction_event_id():
    handler = _handler()

    _stimulate(handler, 'react_message', {
        'message': '👍',
        'room_id': '!room:example.org',
        'event_id': '$message:example.org',
    })

    response = handler.adapter_core.responses[0]
    assert response.name == 'succes'
    assert _parameters(response) == {'code': 200, 'id': '$reaction:example.org'}


def test_announced_parameter_names_match_current_model():
    stimuli = {
        label.name: {parameter.name for parameter in label.parameters}
        for label in Handler().supported_labels()
        if label.sort == Sort.STIMULUS
    }

    assert stimuli['pin_event'] == {'room_id', 'event_id_list'}
    assert stimuli['reply_event'] == {'message', 'room_id', 'event_id'}
    assert stimuli['react_message'] == {'message', 'room_id', 'event_id'}


def test_matrix_api_failure_becomes_model_error_response(caplog):
    class FailingConnection(MatrixConnectionStub):
        def create_room(self, name):
            raise MatrixConnectionError(
                'Matrix API returned HTTP 403: Not allowed',
                status_code=403,
                errcode='M_FORBIDDEN',
            )

    handler = _handler()
    handler.sut = FailingConnection()

    _stimulate(handler, 'create_room', {'name': 'Test room'})

    response = handler.adapter_core.responses[0]
    assert response.name == 'error'
    assert _parameters(response) == {
        'code': 403,
        'error_msg': 'M_FORBIDDEN',
        'error_text': 'Matrix API returned HTTP 403: Not allowed',
    }
    assert "Matrix stimulus 'create_room' failed: Matrix API returned HTTP 403" in caplog.text


def test_http_404_and_405_are_mapped_to_model_supported_error_code():
    for http_status in (404, 405):
        class FailingConnection(MatrixConnectionStub):
            def create_room(self, name):
                raise MatrixConnectionError(
                    f'Matrix API returned HTTP {http_status}: Unrecognized request',
                    status_code=http_status,
                    errcode='M_UNRECOGNIZED',
                )

        handler = _handler()
        handler.sut = FailingConnection()
        _stimulate(handler, 'create_room', {'name': 'Test room'})

        response = handler.adapter_core.responses[0]
        assert response.name == 'error'
        assert _parameters(response) == {
            'code': 400,
            'error_msg': 'M_UNRECOGNIZED',
            'error_text': f'Matrix API returned HTTP {http_status}: Unrecognized request',
        }


def test_empty_input_is_sent_to_matrix_and_matrix_error_is_forwarded():
    class RejectingMatrix(MatrixConnectionStub):
        def create_room(self, name):
            assert name == ''
            raise MatrixConnectionError(
                'Matrix API returned HTTP 400: Invalid room name',
                status_code=400,
                errcode='M_INVALID_PARAM',
            )

    handler = _handler()
    handler.sut = RejectingMatrix()

    _stimulate(handler, 'create_room', {'name': ''})

    response = handler.adapter_core.responses[0]
    assert response.name == 'error'
    assert _parameters(response) == {
        'code': 400,
        'error_msg': 'M_INVALID_PARAM',
        'error_text': 'Matrix API returned HTTP 400: Invalid room name',
    }


def test_start_validates_matrix_and_records_authenticated_user():
    handler = Handler()
    handler.adapter_core = AdapterCoreStub()
    handler.configuration = handler.default_configuration()
    handler.configuration.items[1].value = 'test-token'

    class ValidatingConnection(MatrixConnectionStub):
        def __init__(self, homeserver_url, access_token):
            assert homeserver_url == 'http://localhost:8008'
            assert access_token == 'test-token'

    with patch('matrix.handler.MatrixConnection', ValidatingConnection):
        handler.start()

    assert handler.user_id == '@tester:example.org'
    assert handler.adapter_core.ready_calls == 1
