from . import Game, GameError, ScoreDetector, Deck
import logging
import threading
import uuid


class Server:
    def __init__(self, logger=None):
        self._id = str(uuid.uuid4())
        self._lobby = []
        self._room_size = 2
        self._lock = threading.Lock()
        self._logger = logger if logger else logging

    def new_players(self):
        raise NotImplementedError

    def get_player(self, id):
        for player in self._lobby:
            if player.get_id() == id:
                return player
        return None

    def join_lobby(self, player):
        player.try_send_message({"msg_id": "connect", "server": self._id})

        if player.get_error():
            return

        self._lock.acquire()

        try:
            # Clean-up the lobby
            self._lobby = [p for p in self._lobby if not p.get_error()]

            self._lobby.append(player)
            self._logger.info("Player {} has joined the lobby.".format(player.get_id()))

            for x in self._lobby:
                x.try_send_message({
                    'msg_id': 'join-lobby',
                    'players': [p.dto() for p in self._lobby],
                    'player': player.dto()
                })

            if len(self._lobby) >= self._room_size:
                lowest_rank = 11 - len(self._lobby)
                game = Game(players=self._lobby,
                            deck=Deck(lowest_rank),
                            score_detector=ScoreDetector(lowest_rank),
                            stake=10.0,
                            logger=self._logger)
                thread = threading.Thread(target=Server.play_game, args=(self, game, self._lobby))
                thread.start()
                self._lobby = []
        finally:
            self._lock.release()

    def play_game(self, game, players):
        try:
            self._logger.info("Starting game {}...".format(game.get_id()))

            game.broadcast()

            abort_game = False

            while not abort_game:
                try:
                    game.play_hand()
                    abort_game = game.get_players_in_error()
                except GameError:
                    abort_game = True

            self._logger.info("Aborting game {}...".format(game.get_id()))

            for player in players:
                # Try to send the player a notification
                player.try_send_message({"msg_id": "game-status", "status": 0})
                self.join_lobby(player)
        except:
            # Something terrible happened
            self._logger.exception("Unexpected error happened.")
            for player in players:
                player.disconnect()
            raise

    def start(self):
        for player in self.new_players():
            try:
                # Player successfully connected: joining the lobby
                self._logger.info("Player {} '{}' CONNECTED".format(player.get_id(), player.get_name()))
                self.join_lobby(player)
            except:
                # Close bad connections and ignore the connection
                self._logger.exception("Bad connection")
                pass
