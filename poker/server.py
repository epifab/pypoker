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

    def join_lobby(self, player):
        self._lock.acquire()
        try:
            self._players.append(player)
            self._logger.info("Player {} has joined the lobby.".format(player.get_id()))
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
            self._logger.info("Starting a new game...")

            for player in players:
                player.send_message({"msg_id": "game-status", "status": 1})

            abort_game = False

            while not abort_game:
                game.play_hand()
                abort_game = game.get_players_in_error()

            self._logger.info("Aborting the game...")

            for player in players:
                # Try to send the player a notification
                game_status_sent = player.try_send_message({"msg_id": "game-status", "status": 0})

                if player.get_error() or not game_status_sent:
                    player.disconnect()
                else:
                    self.join_lobby(player)
        except:
            # Something terrible happened
            self._logger.exception("Unexpected error happened.")

            for player in players:
                player.disconnect()
            raise

    def start(self):
        self._socket.listen(1)
        self._logger.info("Poker server listening.")

        while True:
            client_socket, client_address = self._socket.accept()
            self._logger.info("New connection from {}".format(client_address))
            player = PlayerServer(client=JsonSocket(socket=client_socket, address=client_address))
            try:
                # Connecting the remote player
                player.connect()
            except (SocketError, MessageFormatError, MessageTimeout) as e:
                # Communication breakdown
                self._logger.error("Cannot connect the player: {}".format(e.args[0]))
                player.disconnect() # Also closes the socket
            else:
                # Player successfully connected: joining the lobby
                self._logger.info("Player {} '{}' CONNECTED".format(player.get_id(), player.get_name()))
                self.join_lobby(player)
