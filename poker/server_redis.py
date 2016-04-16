from . import Server, PlayerServer, Channel, ChannelError, MessageFormatError, MessageTimeout
import errno
import json
import logging
import redis
import time


class ServerRedis(Server):
    def __init__(self, redis_url, logger=None):
        self._redis = redis.from_url(redis_url)
        self._pubsub = redis.pubsub()
        self._pubsub.subscribe('poker5-connections')
        Server.__init__(self, logger)

    def new_players(self):
        for message in self._pubsub.listen():
            player = Server.validate_connection_message(message)
            yield PlayerServer(channel=RedisChannel(), id=player['id'], name=player['name'], money=player['money'])


class RedisChannel(Channel):
    def __init__(self, logger=None):
        self._connect_message = message
        self._logger = logger if logger else logging

    def close(self):
        raise NotImplementedError

    def send_message(self, message):
        raise NotImplementedError

    def recv_message(self, timeout=None):
        raise NotImplementedError
