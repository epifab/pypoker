from . import Player, MessageFormatError, ChannelError, MessageTimeout, Game
import logging
import time


class PlayerServer(Player, Game.EventListener):
    def __init__(self, channel, id, name, money, logger=None):
        Player.__init__(self, id=id, name=name, money=money)
        self._channel = channel
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
        try:
            self._channel.close()
        except:
            pass

    def update_channel(self, channel):
        self._channel = channel

    def ping(self, pong=False):
        try:
            self.send_message({"msg_id": "ping"})
            if pong:
                message = self.recv_message(timeout=time.time() + 2)
                MessageFormatError.validate_msg_id(message, expected="ping")
            return True
        except (ChannelError, MessageTimeout, MessageFormatError) as e:
            self._logger.error("Unable to ping {}: {}".format(self, e))
            self.disconnect()
            return False

    def try_send_message(self, message):
        try:
            self.send_message(message)
            return True
        except ChannelError as e:
            return False

    def send_message(self, message):
        return self._channel.send_message(message)

    def recv_message(self, timeout=None):
        return self._channel.recv_message(timeout)

    def game_event(self, event, event_data, game_data):
        message = {"msg_id": "game-update"}
        message.update(event_data)
        message.update(game_data)
        self.try_send_message(message)
