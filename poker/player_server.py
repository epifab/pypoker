from . import MessageFormatError, ChannelError, MessageTimeout
import logging
import time


class PlayerServer:
    def __init__(self, player, channel, logger=None):
        self._player = player
        self._channel = channel
        self._connected = True
        self._logger = logger if logger else logging

    def disconnect(self):
        """Disconnect the client"""
        if self._connected:
            self.try_send_message({"message_type": "disconnect"})
            self._channel.close()
            self._connected = False

    @property
    def id(self):
        return self._player.id

    @property
    def name(self):
        return self._player.name

    @property
    def money(self):
        return self._player.money

    def __str__(self):
        return str(self._player)

    @property
    def channel(self):
        return self._channel

    @property
    def connected(self):
        return self._connected

    def update_channel(self, new_player):
        self.disconnect()
        self._channel = new_player.channel
        self._connected = new_player.connected

    def ping(self):
        try:
            self.send_message({"message_type": "ping"})
            message = self.recv_message(timeout_epoch=time.time() + 2)
            MessageFormatError.validate_message_type(message, expected="pong")
            return True
        except (ChannelError, MessageTimeout, MessageFormatError) as e:
            self._logger.error("Unable to ping {}: {}".format(self, e))
            self.disconnect()
            return False

    def try_send_message(self, message):
        try:
            self.send_message(message)
            return True
        except ChannelError:
            return False

    def send_message(self, message):
        return self._channel.send_message(message)

    def recv_message(self, timeout_epoch=None):
        message = self._channel.recv_message(timeout_epoch)
        if "message_type" in message and message["message_type"] == "disconnect":
            raise ChannelError("Client disconnected")
        return message
