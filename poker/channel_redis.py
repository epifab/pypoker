from . import Channel, MessageFormatError, MessageTimeout
import json
import signal
import time


class RedisListener():
    def __init__(self, redis, channel):
        self._pubsub = redis.pubsub()
        self._pubsub.subscribe(channel)

    def close(self):
        self._pubsub.unsubscribe()

    def recv_message(self, timeout_epoch=None):
        def timeout_handler():
            raise MessageTimeout("Timed out")

        if timeout_epoch:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(round(timeout_epoch - time.time())))

        try:
            for message in self._pubsub.listen():
                if message["type"] == "message":
                    break
        finally:
            if timeout_epoch:
                signal.alarm(0)

        try:
            # Deserialize and return the message
            return json.loads(message["data"])
        except ValueError:
            # Invalid json
            raise MessageFormatError(desc="Unable to decode the JSON message")


class RedisPublisher():
    def __init__(self, redis, channel):
        self._redis = redis
        self._channel = channel

    def send_message(self, message):
        # Encode the message
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")
        self._redis.publish(self._channel, msg_encoded)


# class RedisPubSub(Channel):
#     def __init__(self, redis, channel_in, channel_out):
#         self._listener = RedisListener(redis, channel_in)
#         self._publisher = RedisPublisher(redis, channel_out)
#
#     def close(self):
#         self._listener.close()
#
#     def recv_message(self, timeout_epoch=None):
#         return self._listener.recv_message(timeout_epoch)
#
#     def send_message(self, message):
#         self._publisher.send_message(message)


class ChannelRedis(Channel):
    def __init__(self, redis, channel_in, channel_out):
        self._redis = redis
        self._channel_in = channel_in
        self._channel_out = channel_out
        redis.delete(self._channel_in)

    def recv_message(self, timeout_epoch=None):
        response = self._redis.brpop(
            [self._channel_in],
            timeout=int(round(timeout_epoch - time.time())) if timeout_epoch else 0
        )
        if response is None:
            raise MessageTimeout("Timed out")
        try:
            # Deserialize and return the message
            return json.loads(response[1])
        except ValueError:
            # Invalid json
            raise MessageFormatError(desc="Unable to decode the JSON message")

    def send_message(self, message):
        # Encode the message
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")
        self._redis.lpush(self._channel_out, msg_encoded)
        self._redis.expire(self._channel_out, 5)
