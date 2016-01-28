from poker import Game, Deck, ScoreDetector, PlayerServer, JsonSocket
import logging


class Room:
    def __init__(self, socket, size=4, stakes=10.0):
        self._socket = socket
        self._size = size
        self._stakes = stakes
        self._lowest_rank = 11 - size
        self._games = []
        self._players = []

    def start(self):
        while True:
            pass

    def create_game(self):
        return Game(self._players, Deck(self._lowest_rank), ScoreDetector(self._lowest_rank), self._stakes)

    def connect_player(self):
        client, address = self._socket.accept()
        logging.info("New connection from {}".format(address))
        # Initializing the player
        player = PlayerServer(JsonSocket(client))
        logging.info("Player {} '{}' CONNECTED".format(player.get_id(), player.get_name()))
        return player
