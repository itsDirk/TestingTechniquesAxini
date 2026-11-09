import json
import time
from datetime import datetime, timezone

from generic.api import label_pb2
from generic.api.configuration import Configuration, ConfigurationItem
from generic.api.label import Label, Sort
from generic.api.parameter import Parameter
from generic.api.type import Type
from generic.handler import Handler as AbstractHandler
from matrix.matrix_connection import MatrixConnection


def _stimulus(name: str, parameters: list[Parameter]) -> Label:
    return Label(Sort.STIMULUS, name, 'matrix', parameters=parameters)


def _response(name: str, parameters: list[Parameter]) -> Label:
    return Label(Sort.RESPONSE, name, 'matrix', parameters=parameters)


class Handler(AbstractHandler):
    """Maps AMP stimuli to Matrix room creation and text-message requests."""

    def __init__(self):
        super().__init__()
        self.sut = None

    def start(self):
        """Prepare the Matrix API client from the adapter configuration."""
        configuration = {item.name: item.value for item in self.configuration.items}
        homeserver_url = configuration.get('homeserver_url', '').strip()
        access_token = configuration.get('access_token', '').strip()
        self.sut = MatrixConnection(homeserver_url, access_token)
        self.sut.whoami()
        self.adapter_core.send_ready()

    def reset(self):
        """Signal readiness; Matrix state is isolated by creating rooms per test."""
        self.adapter_core.send_ready()

    def stop(self):
        """Discard the stateless HTTP client."""
        self.sut = None

    def stimulate(self, pb_label: label_pb2.Label):
        """Execute one supported Matrix operation and report its result to AMP."""
        if self.sut is None:
            raise RuntimeError('Matrix handler has not been started')

        label = Label.decode(pb_label)
        parameters = {parameter.name: parameter.value for parameter in label.parameters}

        if label.name == 'create_room':
            room_name = self._required_parameter(parameters, 'name')
            result = self.sut.create_room(room_name)
            room_id = self._required_result(result, 'room_id')
            request_payload = {'name': room_name}
            response = _response(
                'room_created',
                [Parameter('room_id', Type.STRING, room_id)],
            )
        elif label.name == 'send_text':
            room_id = self._required_parameter(parameters, 'room_id')
            body = self._required_parameter(parameters, 'body')
            result = self.sut.send_text(room_id, body)
            event_id = self._required_result(result, 'event_id')
            request_payload = {'msgtype': 'm.text', 'body': body}
            response = _response(
                'message_sent',
                [
                    Parameter('room_id', Type.STRING, room_id),
                    Parameter('event_id', Type.STRING, event_id),
                ],
            )
        else:
            raise ValueError(f'Unsupported Matrix stimulus: {label.name}')

        pb_label.timestamp = time.time_ns()
        pb_label.physical_label = json.dumps(request_payload).encode('utf-8')
        self.adapter_core.send_stimulus_confirmation(pb_label)
        response.timestamp = datetime.now(timezone.utc)
        response.physical_label = json.dumps(result).encode('utf-8')
        self.adapter_core.send_response(response)

    def supported_labels(self) -> list[Label]:
        """Return the Matrix operations exposed to the AMP model."""
        return [
            _stimulus(
                'create_room',
                [Parameter('name', Type.STRING)],
            ),
            _response(
                'room_created',
                [Parameter('room_id', Type.STRING)],
            ),
            _stimulus(
                'send_text',
                [
                    Parameter('room_id', Type.STRING),
                    Parameter('body', Type.STRING),
                ],
            ),
            _response(
                'message_sent',
                [
                    Parameter('room_id', Type.STRING),
                    Parameter('event_id', Type.STRING),
                ],
            ),
        ]

    def default_configuration(self) -> Configuration:
        """Return homeserver and token settings required to use the Matrix API."""
        return Configuration([
            ConfigurationItem(
                name='homeserver_url',
                tipe=Type.STRING,
                description='Base URL of the Matrix homeserver Client-Server API',
                value='http://localhost:8008',
            ),
            ConfigurationItem(
                name='access_token',
                tipe=Type.STRING,
                description='Matrix access token for the test user',
                value='syt_a2Fyc3Y_ufrOBaiouaUGymOERHgw_1jkLNS',
            ),
        ])

    @staticmethod
    def _required_parameter(parameters: dict, name: str) -> str:
        value = parameters.get(name)
        if not isinstance(value, str) or not value:
            raise ValueError(f'Matrix stimulus requires a non-empty "{name}" parameter')
        return value

    @staticmethod
    def _required_result(result: dict, name: str) -> str:
        value = result.get(name)
        if not isinstance(value, str) or not value:
            raise ValueError(f'Matrix API response is missing "{name}"')
        return value
