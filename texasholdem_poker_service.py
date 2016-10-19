from poker import GameServerRedis, GameRoomFactory, HoldemPokerGameFactory
import logging
import redis
import os


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger()

    redis_url = os.environ["REDIS_URL"]

    server = GameServerRedis(
        redis=redis.from_url(redis_url),
        connection_channel="texas-holdem-poker:lobby",
        room_factory=GameRoomFactory(
            room_size=5,
            game_factory=HoldemPokerGameFactory(big_blind=40.0, small_blind=20, logger=logger)
        ),
        logger=logger
    )
    server.start()
