from poker import Channel, ChannelError, MessageFormatError, MessageTimeout, Server
import logging
import json
import time
import gevent


class ServerWebSocket(Server):
    def __init__(self, logger=None):
        Server.__init__(self, logger)
        self._new_players = []

    def register(self, player):
        self._new_players.append(player)

    def new_players(self):
        while True:
            if self._new_players:
                yield self._new_players.pop()
            gevent.sleep(0.1)


class MessageReceiver:
    def __init__(self, ws, timeout):
        self.ws = ws
        self.timeout = timeout
        self.message = None
        self.error = False

    def _receive(self):
        try:
            self.message = self.ws.receive()
        except:
            self.error = True

    def receive(self):
        thread = gevent.spawn(self._receive)
        thread.join(int(self.timeout - time.time()))
        if self.error:
            raise ChannelError("Unable to receive data from the remote host")
        elif not self.message:
            raise TimeoutError("Timed out")
        return self.message


class WebSocketChannel(Channel):
    def __init__(self, ws, logger=None):
        self._ws = ws
        self._logger = logger if logger else logging

    def close(self):
        self._ws.close()

    def send_message(self, message):
        if self._ws.closed:
            raise ChannelError("Unable to send data to the remote host (not connected)")

        # Encode the message
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")

        try:
            self._ws.send(msg_encoded)
        except:
            raise ChannelError("Unable to send data to the remote host")

    def recv_message(self, timeout=None):
        # @todo Implement a proper timeout

        if self._ws.closed:
            raise ChannelError("Unable to receive data from the remote host (not connected)")

        message = MessageReceiver(self._ws, timeout).receive()

        if not message:
            raise ChannelError("Unable to receive data from the remote host (message was empty)")
        try:
            # Deserialize and return the message
            return json.loads(message)
        except ValueError:
            # Invalid json
            raise MessageFormatError(desc="Unable to decode the JSON message")
