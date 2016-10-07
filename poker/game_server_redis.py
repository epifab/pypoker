from . import GameServer, PlayerServer, \
    MessageQueue, ChannelRedis, MessageFormatError


class GameServerRedis(GameServer):
    def __init__(self, redis, logger=None):
        GameServer.__init__(self, logger)
        self._redis = redis
        self._message_queue = MessageQueue(redis)
        self._connection_channel = "poker5:lobby"

    def new_players(self):
        while True:
            # Receiving connection requests
            message = self._message_queue.pop(self._connection_channel)

            MessageFormatError.validate_message_type(message, "connect")

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
                channel=ChannelRedis(
                    self._redis,
                    "poker5:player-{}:session-{}:I".format(player_id, session_id),
                    "poker5:player-{}:session-{}:O".format(player_id, session_id)
                ),
                id=player_id,
                name=player_name,
                money=player_money,
                logger=self._logger
            )

            # Acknowledging the connection
            player.send_message({
                "message_type": "connect",
                "server_id": self._id,
                "player": player.dto()
            })

            yield player
