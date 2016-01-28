from poker import Game, ScoreDetector, Deck, PlayerServer, JsonSocket, MessageFormatError, SocketError, MessageTimeout
import socket
import logging
import threading


class Server:
    def __init__(self, host, port, logger=None):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((host, port))
        self._players = []
        self._room_size = 2
        self._lock = threading.Lock()
        self._logger = logger if logger else logging

    def new_player(self, player):
        self._lock.acquire()
        try:
            self._players.append(player)
            if len(self._players) >= self._room_size:
                lowest_rank = 11 - len(self._players)
                game = Game(players=self._players,
                            deck=Deck(lowest_rank),
                            score_detector=ScoreDetector(lowest_rank),
                            stake=10.0)
                thread = threading.Thread(target=Server.play_game, args=(self, game, self._players))
                thread.start()
                self._players = []
        finally:
            self._lock.release()

    def play_game(self, game, players):
        try:
            for player in players:
                player.try_send_message({"msg_id": "game-status", "status": 1})

            abort_game = False

            while not abort_game:
                game.play_hand()

                for player in players:
                    if player.get_error():
                        # self._logger.exception("Player {}: Communication breakdown".format(player.get_id()))
                        player.disconnect()
                        abort_game = True

        except:
            self._logger.exception("Unexpected error happened.")
            raise
        finally:
            self._logger.info("Terminating the game")
            for player in players:
                if not player.get_error():
                    player.try_send_message({"msg_id": "game-status", "status": 0})
                    player.disconnect()

        # Re-add alive players to the waiting list
        for player in players:
            if not player.get_error():
                self.new_player(player)

    def start(self):
        self._socket.listen(1)
        self._logger.info("Poker server listening.")
        players = []
        while True:
            client, address = self._socket.accept()
            self._logger.info("New connection from {}".format(address))
            try:
                # Initializing the player
                player = PlayerServer(client=JsonSocket(socket=client, address=address))
                self._logger.info("Player {} '{}' CONNECTED".format(player.get_id(), player.get_name()))
                self.new_player(player)
            except (socket.error, socket.timeout, MessageFormatError):
                self._logger.exception("Cannot connect the player")
