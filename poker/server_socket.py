from poker import Server, SocketChannel
import socket


class ServerSocket(Server):
    def __init__(self, address, logger=None):
        Server.__init__(self, logger)
        self._address = address
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(address)
        self._socket.listen(1)

    def channels(self):
        while True:
            client_socket, client_address = self._socket.accept()
            self._logger.info("New socket connection from {}".format(client_address))
            channel = SocketChannel(socket=client_socket, address=client_address)
            channel.send_message({'msg_id': 'connect'})
            yield channel
