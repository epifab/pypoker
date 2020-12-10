import time
from typing import Any, Optional

from redis import Redis

from .player import Player
from .channel import MessageFormatError, Channel
from .channel_redis import ChannelRedis, MessageQueue


class PlayerClient:
    def __init__(self, player: Player, connection_message: Any, server_channel: Channel):
        self._player: Player = player
        self._connection_message: Any = connection_message
        self._server_channel: Channel = server_channel

    @property
    def connection_message(self):
        return self._connection_message

    @property
    def player(self) -> Player:
        return self._player

    def send_message(self, message: Any):
        self._server_channel.send_message(message)

    def recv_message(self, timeout_epoch: Optional[float] = None) -> Any:
        return self._server_channel.recv_message(timeout_epoch)

    def close(self):
        self._server_channel.close()


class PlayerClientConnector:
    CONNECTION_TIMEOUT = 30

    def __init__(self, redis: Redis, connection_channel: str, logger):
        self._redis = redis
        self._connection_queue = MessageQueue(redis, connection_channel)
        self._logger = logger

    def connect(self, player: Player, session_id: str, room_id: str) -> PlayerClient:
        # Requesting new connection
        self._connection_queue.push(
            {
                "message_type": "connect",
                "timeout_epoch": time.time() + PlayerClientConnector.CONNECTION_TIMEOUT,
                "player": {
                    "id": player.id,
                    "name": player.name,
                    "money": player.money
                },
                "session_id": session_id,
                "room_id": room_id
            }
        )

        server_channel = ChannelRedis(
            self._redis,
            "poker5:player-{}:session-{}:O".format(player.id, session_id),
            "poker5:player-{}:session-{}:I".format(player.id, session_id)
        )

        # Reading connection response
        connection_message = server_channel.recv_message(time.time() + PlayerClientConnector.CONNECTION_TIMEOUT)
        MessageFormatError.validate_message_type(connection_message, "connect")
        self._logger.info("{}: connected to server {}".format(player, connection_message["server_id"]))
        return PlayerClient(player, connection_message, server_channel)
