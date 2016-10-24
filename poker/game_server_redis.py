from . import GameServer, PlayerServer, \
    MessageQueue, ChannelRedis, ChannelError, MessageFormatError, MessageTimeout
import time


class GameServerRedis(GameServer):
    def __init__(self, redis, connection_channel, room_factory, logger=None):
        GameServer.__init__(self, room_factory, logger)
        self._redis = redis
        self._connection_queue = MessageQueue(redis, connection_channel)

    def _connect_player(self, message):
        try:
            timeout_epoch = int(message["timeout_epoch"])
        except IndexError:
            raise MessageFormatError(attribute="timeout_epoch", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="timeout_epoch", desc="Invalid session id")

        if timeout_epoch < time.time():
            return MessageTimeout("Connection timeout")

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
            logger=self._logger,
            id=player_id,
            name=player_name,
            money=player_money,
        )

        # Acknowledging the connection
        player.send_message({
            "message_type": "connect",
            "server_id": self._id,
            "player": player.dto()
        })

        return player

    def new_players(self):
        while True:
            try:
                yield self._connect_player(self._connection_queue.pop())
            except (ChannelError, MessageTimeout, MessageFormatError) as e:
                self._logger.error("Unable to connect the player: {}".format(e.args[0]))
