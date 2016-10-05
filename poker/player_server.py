from . import Player, MessageFormatError, ChannelError, MessageTimeout
import logging
import time


class PlayerServer(Player):
    def __init__(self, channel, id, name, money, logger=None):
        Player.__init__(self, id=id, name=name, money=money)
        self._channel = channel
        self._connected = True
        self._logger = logger if logger else logging

    def dto(self, with_score=False):
        return {
            "id": self.get_id(),
            "name": self.get_name(),
            "money": self.get_money(),
            "score": self.get_score().dto() if with_score else None
        }

    def disconnect(self):
        """Disconnect the client"""
        if self._connected:
            self._connected = False
            self.try_send_message({"msg_id": "disconnect"})
            self._channel.close()

    @property
    def connected(self):
        return self._connected

    def update_channel(self, channel):
        self._channel = channel

    def ping(self):
        try:
            self.send_message({"msg_id": "ping"})
            message = self.recv_message(timeout_epoch=time.time() + 2)
            MessageFormatError.validate_msg_id(message, expected="pong")
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
        if "msg_id" in message and message["msg_id"] == "disconnect":
            raise ChannelError("Client disconnected")
        return message
