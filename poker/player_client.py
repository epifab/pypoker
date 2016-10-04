from . import Player, ChannelError, MessageTimeout, MessageFormatError
import logging
import time


class PlayerClient(Player):
    CONNECTION_TIMEOUT = 1

    def __init__(self, server_channel, client_channel, id, name, money, logger=None):
        Player.__init__(self, id, name, money)
        self._server_channel = server_channel
        self._client_channel = client_channel
        self._logger = logger if logger else logging

    def connect(self, message_queue, session_id):
        message_queue.push(
            "poker5:lobby",
            {
                "msg_id": "connect",
                "player": {
                    "id": self.get_id(),
                    "name": self.get_name(),
                    "money": self.get_money()
                },
                "session_id": session_id
            }
        )

        connection_message = self._server_channel.recv_message(time.time() + 5)  # 5 seconds

        # Validating message id
        MessageFormatError.validate_msg_id(connection_message, "connect")

        server_id = str(connection_message["server_id"])

        self._logger.info("{}: connected to server {}".format(self, server_id))

        # Forwarding connection message to the client
        self._client_channel.send_message(connection_message)

    def disconnect(self):
        try:
            self._server_channel.send_message({"msg_id": "disconnect"})
        except:
            pass
        self._server_channel.close()

        try:
            self._client_channel.send_message({"msg_id": "disconnect"})
        except:
            pass
        self._client_channel.close()

    def send_message_server(self, message):
        self._logger.debug("{}: sending message to game server: {}".format(self, message))
        self._server_channel.send_message(message)

    def send_message_client(self, message):
        self._logger.debug("{}: sending message to client: {}".format(self, message))
        self._client_channel.send_message(message)

    def recv_message_server(self, timeout_epoch=None):
        message = self._server_channel.recv_message(timeout_epoch)
        self._logger.debug("{}: game server message: {}".format(self, message))
        return message

    def recv_message_client(self, timeout_epoch=None):
        message = self._client_channel.recv_message(timeout_epoch)
        self._logger.debug("{}: client message: {}".format(self, message))
        return message

    def play(self):
        while True:
            message = self.recv_message_server()

            if message["msg_id"] == "ping":
                self.send_message_server({"msg_id": "ping"})
                continue

            # Forward messages to the client
            self.send_message_client(message)

            # Game service disconnection
            if message["msg_id"] == "disconnect":
                self._logger.info("{}: disconnected by the server")
                break

            client_action_needed = message["msg_id"] == "ping" or \
                (message["msg_id"] == "game-update" \
                 and message["event"] == "player-action" \
                 and message["player_id"] == self.get_id())

            if client_action_needed:
                client_message = self.recv_message_client(message["timeout"])
                self.send_message_server(client_message)
