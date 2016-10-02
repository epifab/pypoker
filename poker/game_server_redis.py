from . import GameServer, PlayerServer, \
    ChannelError, RedisListener, ChannelRedis, MessageFormatError


class ChannelRedisWrapper(ChannelRedis):
    def recv_message(self, timeout_epoch=None):
        message = ChannelRedis.recv_message(self, timeout_epoch)
        if "msg_id" in message and message["msg_id"] == "disconnect":
            raise ChannelError("Client disconnected")
        return message


class GameServerRedis(GameServer):
    def __init__(self, redis, logger=None):
        GameServer.__init__(self, logger)
        self._redis = redis
        self._connections_listener = RedisListener(redis, "poker5:server:{}".format(self._id))

    def on_shutdown(self):
        self._connections_listener.close()

    def new_players(self):
        while True:
            message = self._connections_listener.recv_message()

            MessageFormatError.validate_msg_id(message, "connect")

            try:
                session_id = str(message["session_id"])
            except IndexError:
                raise MessageFormatError(attribute="session", desc="Missing attribute")
            except ValueError:
                raise MessageFormatError(attribute="session", desc="Invalid session id")

            try:
                player_id = str(message["player"]["id"])
            except IndexError:
                raise MessageFormatError(attribute="player.id", desc="Missing attribute")
            except ValueError:
                raise MessageFormatError(attribute="player.id", desc="Invalid player id")

            try:
                player_name = str(message["player"]["name"])
            except IndexError:
                raise MessageFormatError(attribute="player.name", desc="Missing attribute")
            except ValueError:
                raise MessageFormatError(attribute="player.name", desc="Invalid player name")

            try:
                player_money = float(message["player"]["money"])
            except IndexError:
                raise MessageFormatError(attribute="player.money", desc="Missing attribute")
            except ValueError:
                raise MessageFormatError(attribute="player.money",
                                         desc="'{}' is not a number".format(message["player"]["money"]))

            player = PlayerServer(
                channel=ChannelRedisWrapper(
                    self._redis,
                    "poker5:server-{}:player-{}:session-{}:I".format(self._id, player_id, session_id),
                    "poker5:server-{}:player-{}:session-{}:O".format(self._id, player_id, session_id)
                ),
                id=player_id,
                name=player_name,
                money=player_money,
                logger=self._logger
            )

            yield player
