import logging
import redis
import os

from poker.game_server_redis import GameServerRedis
from poker.game_room import GameRoomFactory
from poker.poker_game_holdem import HoldemPokerGameFactory


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger()

    redis_url = os.environ["REDIS_URL"]
    redis = redis.from_url(redis_url)

    server = GameServerRedis(
        redis=redis,
        connection_channel="texas-holdem-poker:lobby",
        room_factory=GameRoomFactory(
            room_size=10,
            game_factory=HoldemPokerGameFactory(
                big_blind=40.0,
                small_blind=20.0,
                logger=logger,
                game_subscribers=[]
            )
        ),
        logger=logger
    )
    server.start()
