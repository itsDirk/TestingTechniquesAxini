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

We will be testing the basic messaging functionalities of the SUT such as: creating a room, sending a message and deleting a message.

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

Our model assumes we start in a state where the user has been logged in and authenticated but nothing else has happened. The only event that can take place at the beginning is creating a room. 

Once a room has been created, we enter a loop allowing the following actions:
- Sending a message
- Deleting a message