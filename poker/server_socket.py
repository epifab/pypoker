from poker import Server, SocketChannel, MessageFormatError, PlayerServer
import socket


class ServerSocket(Server):
    def __init__(self, address, logger=None):
        Server.__init__(self, logger)
        self._address = address
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(address)
        self._socket.listen(1)

    def new_players(self):
        while True:
            client_socket, client_address = self._socket.accept()
            self._logger.info("New socket connection from {}".format(client_address))
            channel = SocketChannel(socket=client_socket, address=client_address)
            yield self.connect_player(SocketChannel(socket=client_socket, address=client_address))

    def connect_player(self, channel):
        message = channel.recv_message()

        MessageFormatError.validate_msg_id(message, "connect")

        try:
            id = str(message["player"]["id"])
        except IndexError:
            raise MessageFormatError(attribute="player.id", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.id", desc="Invalid player id")

        try:
            name = str(message["player"]["name"])
        except IndexError:
            raise MessageFormatError(attribute="player.name", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.name", desc="Invalid player name")

        try:
            money = float(message["player"]["money"])
        except IndexError:
            raise MessageFormatError(attribute="player.money", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.money",
                                     desc="'{}' is not a number".format(message["player"]["money"]))

        player = PlayerServer(channel=channel, id=id, name=name, money=money, logger=self._logger)

        player.try_send_message({
            'msg_id': 'connect',
            'player': {
                'id': player.get_id(),
                'name': player.get_name(),
                'money': player.get_money()
            }})

        return player
