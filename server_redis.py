from poker import GameServerRedis, TraditionalPokerGameFactory
import logging
import redis
import os


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger()

    redis_url = os.environ["REDIS_URL"]

    server = GameServerRedis(
        redis=redis.from_url(redis_url),
        game_factory=TraditionalPokerGameFactory(blind=10.0),
        logger=logger
    )
    server.start()
