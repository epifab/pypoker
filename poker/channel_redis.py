from . import Channel, MessageFormatError, MessageTimeout, ChannelError
from redis import exceptions
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
        def timeout_handler(signum, frame):
            raise MessageTimeout("Timed out")

        if timeout_epoch:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(round(timeout_epoch - time.time())))

        try:
            for message in self._pubsub.listen():
                if message["type"] == "message":
                    return json.loads(message["data"])
        except ValueError:
            # Invalid json
            raise MessageFormatError(desc="Unable to decode the JSON message")
        finally:
            if timeout_epoch:
                signal.alarm(0)


class RedisPublisher():
    def __init__(self, redis, channel):
        self._redis = redis
        self._channel = channel

    def send_message(self, message):
        # Encode the message
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")
        self._redis.publish(self._channel, msg_encoded)


class RedisPubSub(Channel):
    def __init__(self, redis, channel_in, channel_out):
        self._listener = RedisListener(redis, channel_in)
        self._publisher = RedisPublisher(redis, channel_out)

    def close(self):
        self._listener.close()

    def recv_message(self, timeout_epoch=None):
        return self._listener.recv_message(timeout_epoch)

    def send_message(self, message):
        self._publisher.send_message(message)


class MessageQueue:
    def __init__(self, redis, queue_name, expire=300):
        self._redis = redis
        self._queue_name = queue_name
        self._expire = expire

    @property
    def name(self):
        return self._queue_name

    def push(self, message):
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")
        try:
            self._redis.lpush(self._queue_name, msg_encoded)
            self._redis.expire(self._queue_name, self._expire)
        except exceptions.RedisError as e:
            raise ChannelError(e.args[0])

    def pop(self, timeout_epoch=None):
        while timeout_epoch is None or time.time() < timeout_epoch:
            try:
                response = self._redis.rpop(self._queue_name)
                if response is not None:
                    try:
                        # Deserialize and return the message
                        return json.loads(response)
                    except ValueError:
                        # Invalid json
                        raise MessageFormatError(desc="Unable to decode the JSON message")
                else:
                    # Context switching
                    gevent.sleep(0.01)
            except exceptions.RedisError as ex:
                raise ChannelError(ex.args[0])
        raise MessageTimeout("Timed out")


class ChannelRedis(Channel):
    def __init__(self, redis, channel_in, channel_out):
        self._queue_in = MessageQueue(redis, channel_in)
        self._queue_out = MessageQueue(redis, channel_out)

    def send_message(self, message):
        self._queue_out.push(message)

    def recv_message(self, timeout_epoch=None):
        return self._queue_in.pop(timeout_epoch)
