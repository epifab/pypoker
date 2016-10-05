from . import Channel, MessageFormatError, MessageTimeout
import gevent
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


class MessageQueue:
    def __init__(self, redis):
        self._redis = redis

    def push(self, name, message):
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")
        self._redis.lpush(name, msg_encoded)
        self._redis.expire(name, 5)

    def pop(self, name, timeout_epoch=None):
        while timeout_epoch is None or time.time() < timeout_epoch:
            response = self._redis.rpop(name)
            if response is not None:
                try:
                    # Deserialize and return the message
                    return json.loads(response)
                except ValueError:
                    # Invalid json
                    raise MessageFormatError(desc="Unable to decode the JSON message")
            else:
                # Context switching
                gevent.sleep(0.1)
        raise MessageTimeout("Timed out")


class ChannelRedis(MessageQueue, Channel):
    def __init__(self, redis, channel_in, channel_out):
        MessageQueue.__init__(self, redis)
        self._channel_in = channel_in
        self._channel_out = channel_out

    def send_message(self, message):
        self.push(self._channel_out, message)

    def recv_message(self, timeout_epoch=None):
        return self.pop(self._channel_in, timeout_epoch)
