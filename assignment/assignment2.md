# Assignment 2
---
- Robin Brevink
- Bas Schram
- Dirk van Roosmalen
- Kars Visscher
---

# Model-Based Testing: AMP and your SUT
## Exericise 2: Description of SUT and test scope

We begin by giving a short summarization of our SUT taken from the first assignment.

Our system-under-test is [Synapse](https://github.com/element-hq/synapse) (v1.164.2), a (home)server developed by [Element](https://element.io/). Synapse is an open source instance of [Matrix](https://matrix.org/) (v1.19) written in Python. Using Synapse, the user can locally run a chat server and connect to it using a web client on [app.element.io](https://app.element.io/). These enable communication in accordance with the Matrix communication protocol. Therefore we will create a model of the Matrix communication protocol and test whether Synapse complies with this protocol.

We will be testing the basic messaging functionalities of the SUT such as: creating a room, sending a message and deleting a message ==TODO update==.  

The interface utilized during testing is the client-server API. Relevant documentation can be found in the [Matrix specification](https://spec.matrix.org/v1.19/client-server-api/). Refer to the following chapters:

| Feature             | Relevant Chapter                                                                         |
| ------------------- | ---------------------------------------------------------------------------------------- |
| Errors              | [Chapter 1.1](https://spec.matrix.org/v1.19/client-server-api/#standard-error-response)  |
| Logging in          | [Chapter 4.3](https://spec.matrix.org/v1.19/client-server-api/#login)                    |
| Sending room events | [Chapter 7.7](https://spec.matrix.org/v1.19/client-server-api/#sending-events-to-a-room) |
| Deleting an event   | [Chapter 7.9](https://spec.matrix.org/v1.19/client-server-api/#redactions)       |
| Creating a room     | [Chapter 8.2](https://spec.matrix.org/v1.19/client-server-api/#creation)                 |
| Sending a message   | [Chapter 10.2](https://spec.matrix.org/v1.19/client-server-api/#instant-messaging)       |


## Exericise 3: Description of the Model

Compared to the testing domain of assignment 1, we have decided to drop tests expecting HTTP status codes 404 (Not Found) and 405 (Method Not Allowed), as they concern invalid HTTP endpoints, and the only way to conclude an endpoint does not exist would be to specify all Matrix endpoints that do exist.

Our model assumes we start in a state where the user is logged in and is authenticated, but no other actions have been executed. For technical reasons, it is also assumed that the user's requests are not subject to rate limiting. The only event that can take place in this state is room creation. Once a room has been created, we enter a loop where any of the following actions are allowed to take place:
- Sending a message
- Deleting a message
- Editing a message
- Pinning a message
- Replying to a message (with another message)
- Reacting to a message (with an emoji)

The loop follows a simple request-response format, so we will explain all possible transitions in a table following this format. For each possible action we have a corresponding stimulus in the Axini model. The possible responses are either a success or error response, which all have the same format. 

| Action                | Stimulus      | Parameters                                                     | Constraints |
| --------------------- | ------------- | -------------------------------------------------------------- | ----------- |
| Creating a room       | create_room   | name : String                                                  | ==TODO==    |
| Leaving a room        | leave_room    | room_id : String<br>user_id : String                           |             |
| Sending a message     | send_message  | message : String<br>room_id : String                           |             |
| Deleting a message    | redact_event  | event_id : String<br>room_id : String<br>redaction_id : String |             |
| Editing a message     | replace_event | message : String<br>room_id : String<br>event_id : String      |             |
| Pinning a message     | pin_event     | room_id : String<br>event_id_list : \[String]                  |             |
| Replying to a message | reply_event   | message : String<br>room_id : String<br>event_id : String      |             |
| Reacting to a message | react_message | message : String<br>room_id : String<br>event_id : String      |             |
Next to the stimuli are listed the constraints for which the parameters are considered valid. It is assumed a stimulus is only valid if and only if all parameters have valid values.

| Reponse | Parameters                                                  |
| ------- | ----------------------------------------------------------- |
| succes  | code : integer<br>id : String                               |
| error   | code : integer<br>error_msg : String<br>error_text : String |


The SUT follows a simple request-reponse format. Therefore for each state we describe the accepted stimuli alongside the possible accepted responses.


| Initial<br>State | Accepted Stimulus | Constraints                                                             | Accepted Response | Constraints        | Resulting<br>State |
| ---------------- | ----------------- | ----------------------------------------------------------------------- | ----------------- | ------------------ | ------------------ |
| roomless         | create_room       | room_id is valid                                                        | success<br>       | code is 200        | room               |
| roomless         | create_room       | room_id is not valid                                                    | error             | code is 400 or 403 | roomless           |
| room             | send_message      | message is valid && room_id is current_room_id                          | success           | code is 200        | room               |
| room             | send_message      | message is not valid \|\| room_id is not current_room_id                | error             | code is 400 or 403 | room               |
| room             | redact_event      | event_id exists && room_id is current_room_id && redaction_id is unique |                   |                    |                    |

## Exericise 4: Adapter
The plugin adapter is situated between the remote AMP and our locally run SUT. It's primary purpose is to facilitate a connection between the two. 

A set of functionally identical plugin adapters was provided by [Axini](https://github.com/Axini) in 5 different programming languages. Because of our shared proficiency with Python, we picked the [Python Plugin Adapter](https://github.com/Axini/smartdoor-adapter-python). This PA contained the implementation for the Smartdoor assignment, which we modified to support communication with Synapse instead while keeping in mind [best practices](https://course02.axini.com/docs/tech/adapters/adapter_best_practices.html).     

The `handler.py` translates AMP model labels into Matrix API calls, which is implemented by using a separate function for every type of stimulus in the model contract to translate it and its arguments into an object that is passed to `matrix_connection.py` to build valid HTTP request with those arguments as parameters. The SUT's response is translated in a similar way and in the opposite direction. In successful requests, this is done by extracting the HTTP status code `code=200` and room/event/state-event ID `id` and sending them back as arguments for a `!success` response. For unsuccessful requests, the HTTP status code `code`, meaning of this code `error_msg` and explanation of what went wrong `error_text` are sent back as arguments for a `!error` response.

The `matrix_connection.py` acts as a small authenticated HTTP client for Synapse's Matrix client-server API. It takes the objects generated by `handler.py` and translates them into actual HTTP requests, which are executed. The responses of which are parsed and send back to the `handler.py` for translation. Although the plugin adapter runs locally on the same device as the SUT, the URL of the Synapse homeserver and the access token for the authenticated user are part of the configuration, which can be entered in AMP in the *Adapter* tab. 

## Exericise 5: Test Architecture

![Test Architecture](test-setup.drawio.png)

The diagram shows that the test architecture consists out of 3 main parts: the Axini Modeling Platform (AMP), the adapter, and the SUT. AMP is responsible for hosting the model (based on the specifications of Matrix) and generating / validating tests based on this model. These tests consist out of generating stimuli (asking the SUT to do something) and validating the received responses (the reaction of the SUT). All allowed stimuli and responses are defined in the model.

The adapter is responsible for converting the stimuli into requests the SUT can actually understand and passing them on. When the adapter receives a response back, it needs to translate this back into the language AMP understands and pass it back to the testing platform.

Our SUT (Synapse) runs locally in a Docker container. It receives HTTP requests from the adapter and handles them through the Client-Server API. Once it has finished processing the request, it sends an HTTP response stating whether the request was a succes or whether there was an error during processing/handling.