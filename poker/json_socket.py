import json
import logging


class JsonSocket:
    def __init__(self, socket):
        self._socket = socket

    def close(self):
        self._socket.close()

    def send_message(self, message):
        try:
            # Encode the message
            serialized = json.dumps(message)
            encoded = serialized.encode('utf-8')
            logging.debug("Sending message to {}: {}".format(self._socket.getpeername(), serialized))
            # Sends message length
            self._socket.send(bytes(str(len(encoded)) + "\n", 'utf-8'))
            # Sends the message
            self._socket.sendall(encoded)
        except:
            logging.exception("Unable to send a JSON message to {}".format(self._socket.getpeername()))
            raise

    def recv_message(self, timeout=None):
        default_timeout = self._socket.gettimeout()
        try:
            self._socket.settimeout(timeout)
            # Read the message length
            msg_len_bytes= b''
            char = self._socket.recv(1)
            while char != b'\n':
                msg_len_bytes += char
                char = self._socket.recv(1)
            msg_len = int(msg_len_bytes.decode('utf-8'))
            # Read the message
            encoded = self._socket.recv(msg_len)
            # Decode the message
            serialized = encoded.decode('utf-8')
            logging.debug("Received message from {}: {}".format(self._socket.getpeername(), serialized))
            return json.loads(serialized)
        except:
            logging.exception("Unable to receive a JSON message from {}".format(self._socket.getpeername()))
            raise
        finally:
            self._socket.settimeout(default_timeout)
