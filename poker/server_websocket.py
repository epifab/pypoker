from poker import Channel, ChannelError, MessageTimeout, Server, PlayerServer
import logging
import json
import time
import gevent
from flask import session


class ServerWebSocket(Server):
    def __init__(self, logger=None):
        Server.__init__(self, logger)
        self._new_players = []

    def register(self, ws, id, name, money):
        self._new_players.append(
                PlayerServer(
                        channel=WebSocketChannel(ws),
                        id=id,
                        name=name,
                        money=money))

    def new_players(self):
        while True:
            if self._new_players:
                yield self._new_players.pop()
            gevent.sleep(0.1)

    def connect_player(self, channel):
        return


class WebSocketChannel(Channel):
    def __init__(self, ws, logger=None):
        self._ws = ws
        self._logger = logger if logger else logging

    def close(self):
        pass

    def send_message(self, message):
        # Encode the message
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")

        try:
            # Sends the message
            self._ws.send(msg_encoded)
        except:
            raise ChannelError("Unable to send data to the remote host")

    def recv_message(self, timeout=None):
        # @todo Implement a proper timeout
        try:
            message = self._ws.receive()
        except:
            raise ChannelError("Unable to receive data from the remote host")
        else:
            if timeout and time.time() > timeout:
                raise MessageTimeout("Timed out")
            return message
