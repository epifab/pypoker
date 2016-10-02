from poker import GameServerRedis
import logging
import redis
import os


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger()

    redis_url = "redis://localhost" if "REDIS_URL" not in os.environ else os.environ["REDIS_URL"]

    server = GameServerRedis(redis.from_url(redis_url), logger=logger)
    server.start()
