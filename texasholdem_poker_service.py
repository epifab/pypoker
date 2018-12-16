from poker import GameServerRedis, GameRoomFactory, HoldemPokerGameFactory
from poker.game_persistence import MongoGameSubscriber
import pymongo
import logging
import redis
import os


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger()

    redis_url = os.environ["REDIS_URL"]
    redis = redis.from_url(redis_url)

    # mongo_url = os.environ["MONGODB_URL"]
    # mongo_db = pymongo.MongoClient(mongo_url).get_default_database()

    server = GameServerRedis(
        redis=redis,
        connection_channel="texas-holdem-poker:lobby",
        room_factory=GameRoomFactory(
            room_size=10,
            game_factory=HoldemPokerGameFactory(
                big_blind=40.0,
                small_blind=20.0,
                logger=logger,
                game_subscribers=[
                    # Uncomment the following line to save game events to a games collection
                    # MongoGameSubscriber(mongo_db)
                ]
            )
        ),
        logger=logger
    )
    server.start()
