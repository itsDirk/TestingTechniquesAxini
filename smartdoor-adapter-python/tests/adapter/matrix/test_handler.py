from generic.api.label import Label, Sort
from generic.api.parameter import Parameter
from generic.api.type import Type
from matrix.handler import Handler


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
    def create_room(self, name):
        assert name == 'Test room'
        return {'room_id': '!room:example.org'}

    def send_text(self, room_id, body):
        assert room_id == '!room:example.org'
        assert body == 'Hello Matrix'
        return {'event_id': '$event:example.org'}


def _stimulus(name, parameters):
    return Label(Sort.STIMULUS, name, 'matrix', parameters=parameters).encode()


def test_create_room_stimulus_reports_room_id():
    handler = Handler()
    handler.adapter_core = AdapterCoreStub()
    handler.sut = MatrixConnectionStub()

    handler.stimulate(_stimulus(
        'create_room',
        [Parameter('name', Type.STRING, 'Test room')],
    ))

    assert len(handler.adapter_core.confirmations) == 1
    response = handler.adapter_core.responses[0]
    assert response.name == 'room_created'
    assert response.parameters[0].value == '!room:example.org'


def test_send_text_stimulus_reports_event_id():
    handler = Handler()
    handler.adapter_core = AdapterCoreStub()
    handler.sut = MatrixConnectionStub()

    handler.stimulate(_stimulus(
        'send_text',
        [
            Parameter('room_id', Type.STRING, '!room:example.org'),
            Parameter('body', Type.STRING, 'Hello Matrix'),
        ],
    ))

    response = handler.adapter_core.responses[0]
    assert response.name == 'message_sent'
    assert {parameter.name: parameter.value for parameter in response.parameters} == {
        'room_id': '!room:example.org',
        'event_id': '$event:example.org',
    }


def test_reset_marks_adapter_ready_without_resetting_matrix_state():
    handler = Handler()
    handler.adapter_core = AdapterCoreStub()

    handler.reset()

    assert handler.adapter_core.ready_calls == 1


def test_start_validates_matrix_and_marks_adapter_ready():
    handler = Handler()
    handler.adapter_core = AdapterCoreStub()
    handler.configuration = handler.default_configuration()
    handler.configuration.items[0].value = 'https://matrix.example.org'
    handler.configuration.items[1].value = 'test-token'

    class ValidatingConnectionStub(MatrixConnectionStub):
        def __init__(self, homeserver_url, access_token):
            assert homeserver_url == 'https://matrix.example.org'
            assert access_token == 'test-token'
            self.whoami_called = False

        def whoami(self):
            self.whoami_called = True
            return {'user_id': '@tester:example.org'}

    from unittest.mock import patch

    with patch('matrix.handler.MatrixConnection', ValidatingConnectionStub):
        handler.start()

    assert handler.sut.whoami_called
    assert handler.adapter_core.ready_calls == 1
