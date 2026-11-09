## Description
This project defines a *Python* plugin adapter that connects the Axini Modeling Platform (AMP) to a Matrix homeserver's Client-Server API.

See https://github/axini and the plugin-adapter-protocol repository for some general information on Axini's plugin adapter protocol. Axini's training on "plugin adapters" provides additional and more detailed information.

The software is distributed under the MIT license, see LICENSE.txt.

## Running the adapter
### Prerequisites
This example adapter is depended on Python (>= 3.11) and uses `pip` for its dependency management. The steps below presume that the `python` and `pip` commands are resolvable in your shell.

### Setting it up
- Clone this repository.
- Open a terminal or command prompt.
- (OPTIONAL) Create a separate virtual environment and activate it `python -m venv <name_of_virtual_env_dir>` and `source <name_of_virtual_env_dir>/bin/activate`
- Perform `pip install -r ./requirements.txt`. This should download all the required dependencies.

### Starting the adapter

Use the following command:

```bash
python src/adapter/plugin_adapter.py -u <url> -t <token>
```

Or the provided convenience script:

```bash
./adapter
```

### Running the tests
- Open a terminal or command prompt.
- Install the test dependencies `pip install -r tests/requirements.txt`.
- Run the tests `pytest tests/`.

### Generating the documentation
- Open a terminal or command prompt.
- Go to `docs/`.
- Run `make html`.
- Documentation is generated under `docs/_build`.

## Matrix model operations

The Matrix-specific implementation is in `src/adapter/matrix`. It currently supports the `matrix7` channel and these stimuli:

| Stimulus | Parameters | Matrix operation |
|---|---|---|
| `create_room` | `name: string` | Create a room; success ID is the Matrix room ID. |
| `leave_room` | `room_id: string`, `user_id: string` | Leave as the configured user; `user_id` must match that user's Matrix ID. |
| `send_message` | `message: string`, `room_id: string` | Send an `m.text` event; success ID is the event ID. |
| `redact_event` | `event_id: string`, `room_id: string`, `redaction_id: string` | Redact an event; `redaction_id` is the Matrix transaction ID. |
| `replace_message` | `message: string`, `room_id: string`, `event_id: string` | Send an `m.replace` edit event. |
| `pin_event` | `room_id: string`, `event_id_list: [string]` | Set the room's pinned-event state to this list. |
| `reply_event` | `message: string`, `room_id: string`, `event_id: string` | Send a text reply linked to the target event. |
| `react_message` | `message: string`, `room_id: string`, `event_id: string` | Use `message` as the `m.annotation` reaction key. |

Every successful operation responds with `succes(code: integer, id: string)`. The ID is the created Matrix room/event/state-event ID; leaving a room returns its room ID. Matrix failures and invalid model inputs respond with `error(code, error_msg, error_text)`.

To add an operation, add its parameter schema to `Handler.STIMULUS_PARAMETERS`, add a method that translates the parameters to a `MatrixConnection` call and returns the relevant Matrix ID, and register that method in `Handler.operations`. Add tests for the label contract, API request, and handler mapping.

The AMP-related code is stored in `src/adapter/generic` and can be reused by other Python plugin adapters. Matrix-specific labels and API behavior are in `src/adapter/matrix`.

### Threads
The main thread of the adapter ensures that messages from AMP are received and handled. Matrix API requests use HTTP and are made by the Matrix handler while AMP stimuli are processed.

The class QThread (in src/adapter/generic) manages a Queue of items and a Thread. Items can be added to the Queue and the Thread processes items from the queue in a FIFO manner. The Queue can also be emptied. The plugin adapter (class AdapterCore in src/adapter/generic) uses two QThreads for (i) handling messages from AMP and (ii) sending messages to AMP. This ensures that messages from AMP (stimuli) and the SUT (responses) are serviced immediately: any resulting message is added to a queue of pending messages which is processed by either one of the two QThreads.

Using a separate QThread for sending the responses to AMP ensures that only a single WebSocket message can be in transit to AMP.

The QThread for messages from AMP (Configuration, Ready, stimuli) is needed because processing Protobuf messages and Matrix API requests may take time. The WebSocket library is single threaded, so the adapter uses a separate QThread to handle AMP messages while the WebSocket thread remains available for heartbeats and other incoming messages.

The plugin adapter and all its threads are set to run forever. No code is added to gracefully terminate the adapter and its threads. Consequently, when terminating the adapter with Ctrl-C, you will observe several Exceptions on the stderr. This is harmless, though.
