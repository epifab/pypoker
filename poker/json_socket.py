import json


class JsonSocket():
    def __init__(self, socket):
        self._socket = socket

    def send_message(self, message):
        # Encode the message
        serialized = json.dumps(message)
        encoded = serialized.encode('utf-8')
        # Sends message length
        self._socket.send(bytes(str(len(encoded)) + "\n", 'utf-8'))
        # Sends the message
        self._socket.sendall(encoded)

    def recv_message(self):
        try:
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
            return json.loads(serialized)
        except (TypeError, ValueError):
            raise Exception('Unable to parse JSON')
