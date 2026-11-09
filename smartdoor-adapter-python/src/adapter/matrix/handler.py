import json
import logging
import time
from datetime import datetime, timezone

from generic.api import label_pb2
from generic.api.configuration import Configuration, ConfigurationItem
from generic.api.label import Label, Sort
from generic.api.parameter import Parameter
from generic.api.type import Type
from generic.handler import Handler as AbstractHandler
from matrix.matrix_connection import MatrixConnection, MatrixConnectionError


MATRIX_CHANNEL = 'matrix7'


class Handler(AbstractHandler):
    """Maps model stimuli to Matrix Client-Server API operations."""

    STIMULUS_PARAMETERS = {
        'create_room': [('name', Type.STRING)],
        'leave_room': [('room_id', Type.STRING), ('user_id', Type.STRING)],
        'send_message': [('message', Type.STRING), ('room_id', Type.STRING)],
        'redact_event': [
            ('event_id', Type.STRING),
            ('room_id', Type.STRING),
            ('redaction_id', Type.STRING),
        ],
        'replace_message': [
            ('message', Type.STRING),
            ('room_id', Type.STRING),
            ('event_id', Type.STRING),
        ],
        'pin_event': [('room_id', Type.STRING), ('event_id_list', Type.ARRAY)],
        'reply_event': [
            ('message', Type.STRING),
            ('room_id', Type.STRING),
            ('event_id', Type.STRING),
        ],
        'react_message': [
            ('message', Type.STRING),
            ('room_id', Type.STRING),
            ('event_id', Type.STRING),
        ],
    }

    def __init__(self):
        super().__init__()
        self.sut = None
        self.user_id = None
        self.operations = {
            'create_room': self._create_room,
            'leave_room': self._leave_room,
            'send_message': self._send_message,
            'redact_event': self._redact_event,
            'replace_message': self._replace_message,
            'pin_event': self._pin_event,
            'reply_event': self._reply_event,
            'react_message': self._react_message,
        }

    def start(self):
        """Create the Matrix API client, validate its token, and become ready."""
        configuration = {item.name: item.value for item in self.configuration.items}
        homeserver_url = configuration.get('homeserver_url', '').strip()
        access_token = configuration.get('access_token', '').strip()
        self.sut = MatrixConnection(homeserver_url, access_token)
        self.user_id = self._required_string(self.sut.whoami(), 'user_id')
        self.adapter_core.send_ready()

    def reset(self):
        """Matrix data persists; test cases should use their own rooms."""
        self.adapter_core.send_ready()

    def stop(self):
        """Discard the HTTP client and authenticated user identity."""
        self.sut = None
        self.user_id = None

    def stimulate(self, pb_label: label_pb2.Label):
        """Run one supported operation and return a model-shaped response."""
        if self.sut is None:
            raise RuntimeError('Matrix handler has not been started')

        label = Label.decode(pb_label)
        parameters = {parameter.name: parameter.value for parameter in label.parameters}
        pb_label.timestamp = time.time_ns()
        pb_label.physical_label = json.dumps(parameters).encode('utf-8')
        self.adapter_core.send_stimulus_confirmation(pb_label)

        try:
            operation = self.operations.get(label.name)
            if operation is None:
                raise ValueError(f'Unsupported Matrix stimulus: {label.name}')
            response_id, result = operation(parameters)
            response = self._success_response(response_id)
        except (MatrixConnectionError, ValueError) as error:
            logging.error("Matrix stimulus '%s' failed: %s", label.name, error)
            response = self._error_response(error)
            result = {'error': str(error)}

        response.timestamp = datetime.now(timezone.utc)
        response.physical_label = json.dumps(result).encode('utf-8')
        self.adapter_core.send_response(response)

    def _create_room(self, parameters: dict) -> tuple[str, dict]:
        result = self.sut.create_room(self._required_string(parameters, 'name'))
        return self._required_string(result, 'room_id'), result

    def _leave_room(self, parameters: dict) -> tuple[str, dict]:
        room_id = self._required_string(parameters, 'room_id')
        user_id = self._required_string(parameters, 'user_id')
        if user_id != self.user_id:
            raise ValueError(
                f'leave_room user_id must match the authenticated Matrix user {self.user_id}'
            )
        result = self.sut.leave_room(room_id)
        return room_id, result

    def _send_message(self, parameters: dict) -> tuple[str, dict]:
        result = self.sut.send_message(
            self._required_string(parameters, 'room_id'),
            self._required_string(parameters, 'message'),
        )
        return self._required_string(result, 'event_id'), result

    def _redact_event(self, parameters: dict) -> tuple[str, dict]:
        result = self.sut.redact_event(
            self._required_string(parameters, 'room_id'),
            self._required_string(parameters, 'event_id'),
            self._required_string(parameters, 'redaction_id'),
        )
        return self._required_string(result, 'event_id'), result

    def _replace_message(self, parameters: dict) -> tuple[str, dict]:
        result = self.sut.replace_message(
            self._required_string(parameters, 'room_id'),
            self._required_string(parameters, 'event_id'),
            self._required_string(parameters, 'message'),
        )
        return self._required_string(result, 'event_id'), result

    def _pin_event(self, parameters: dict) -> tuple[str, dict]:
        room_id = self._required_string(parameters, 'room_id')
        event_ids = self._required_string_array(parameters, 'event_id_list')
        result = self.sut.pin_events(room_id, event_ids)
        return self._required_string(result, 'event_id'), result

    def _reply_event(self, parameters: dict) -> tuple[str, dict]:
        result = self.sut.reply_message(
            self._required_string(parameters, 'room_id'),
            self._required_string(parameters, 'event_id'),
            self._required_string(parameters, 'message'),
        )
        return self._required_string(result, 'event_id'), result

    def _react_message(self, parameters: dict) -> tuple[str, dict]:
        result = self.sut.react_message(
            self._required_string(parameters, 'room_id'),
            self._required_string(parameters, 'event_id'),
            self._required_string(parameters, 'message'),
        )
        return self._required_string(result, 'event_id'), result

    def _success_response(self, response_id: str) -> Label:
        return Label(
            Sort.RESPONSE,
            'succes',
            MATRIX_CHANNEL,
            parameters=[
                Parameter('code', Type.INTEGER, 200),
                Parameter('id', Type.STRING, response_id),
            ],
        )

    def _error_response(self, error: Exception) -> Label:
        status_code = (
            error.status_code
            if isinstance(error, MatrixConnectionError) and error.status_code
            else 400
        )
        error_code = (
            error.errcode
            if isinstance(error, MatrixConnectionError) and error.errcode
            else type(error).__name__
        )
        return Label(
            Sort.RESPONSE,
            'error',
            MATRIX_CHANNEL,
            parameters=[
                Parameter('code', Type.INTEGER, status_code),
                Parameter('error_msg', Type.STRING, error_code),
                Parameter('error_text', Type.STRING, str(error)),
            ],
        )

    def supported_labels(self) -> list[Label]:
        """Generate the AMP label announcement from the model-facing schema."""
        stimuli = [
            Label(
                Sort.STIMULUS,
                name,
                MATRIX_CHANNEL,
                parameters=[
                    Parameter(
                        parameter_name,
                        parameter_type,
                        ['event_id'] if parameter_type == Type.ARRAY else None,
                    )
                    for parameter_name, parameter_type in parameter_specs
                ],
            )
            for name, parameter_specs in self.STIMULUS_PARAMETERS.items()
        ]
        return stimuli + [
            Label(
                Sort.RESPONSE,
                'error',
                MATRIX_CHANNEL,
                parameters=[
                    Parameter('code', Type.INTEGER),
                    Parameter('error_msg', Type.STRING),
                    Parameter('error_text', Type.STRING),
                ],
            ),
            Label(
                Sort.RESPONSE,
                'succes',
                MATRIX_CHANNEL,
                parameters=[
                    Parameter('code', Type.INTEGER),
                    Parameter('id', Type.STRING),
                ],
            ),
        ]

    def default_configuration(self) -> Configuration:
        """Return homeserver and access-token settings for Matrix."""
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
                value='',
            ),
        ])

    @staticmethod
    def _required_string(parameters: dict, name: str) -> str:
        value = parameters.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'Matrix input requires a non-empty "{name}" string')
        return value

    @classmethod
    def _required_string_array(cls, parameters: dict, name: str) -> list[str]:
        value = parameters.get(name)
        if not isinstance(value, list) or not value:
            raise ValueError(f'Matrix input requires a non-empty "{name}" string array')
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f'Every item in "{name}" must be a non-empty string')
        return value
