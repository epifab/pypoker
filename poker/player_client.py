from . import ChannelRedis, MessageQueue, MessageFormatError
import time


class PlayerClientConnector:
    CONNECTION_TIMEOUT = 30

    def __init__(self, redis, connection_channel, logger):
        self._redis = redis
        self._connection_queue = MessageQueue(redis, connection_channel)
        self._logger = logger

    def connect(self, player, session_id):
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
                "session_id": session_id
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


class PlayerClient:
    def __init__(self, player, connection_message, server_channel):
        self._player = player
        self._connection_message = connection_message
        self._server_channel = server_channel

    @property
    def connection_message(self):
        return self._connection_message

    @property
    def player(self):
        return self._player

    def send_message(self, message):
        self._server_channel.send_message(message)

    def recv_message(self, timeout_epoch=None):
        return self._server_channel.recv_message(timeout_epoch)

    def close(self):
        self._server_channel.close()
