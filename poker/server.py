from . import Game, GameError, ScoreDetector, Deck
import logging
import threading
import random
import string


class Server:
    def __init__(self, logger=None):
        self._id = ''.join(random.choice(string.ascii_lowercase) for i in range(5))
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
        if not player.try_send_message({"msg_id": "connect", "server": self._id}):
            return

        self._lock.acquire()

        try:
            # Clean-up the lobby
            self._lobby = [p for p in self._lobby if p.try_send_message({"msg_id": "ping"})]

            self._lobby.append(player)
            self._logger.info("SERVER({}) player {} has joined the lobby.".format(self._id, player.get_id()))

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
            self._logger.info("SERVER({}) starting game {}".format(self._id, game.get_id()))

            game.broadcast()
            game.play_game()

            for player in players:
                # Try to send the player a notification
                player.try_send_message({"msg_id": "game-status", "status": 0})
                self.join_lobby(player)
        except:
            # Something terrible happened
            self._logger.exception("SERVER({}) unhandled game exception for game {}".format(self._id, game.get_id()))
            for player in players:
                player.disconnect()
            raise
        finally:
            self._logger.info("SERVER({}) terminated game {}".format(self._id, game.get_id()))

    def start(self):
        self._logger.info("SERVER({}) running".format(self._id))
        try:
            for player in self.new_players():
                try:
                    # Player successfully connected: joining the lobby
                    self._logger.info("SERVER({}) player {} connected".format(
                                      self._id, player.get_id(), player.get_name()))
                    self.join_lobby(player)
                except:
                    # Close bad connections and ignore the connection
                    self._logger.exception("SERVER({}) bad connection".format(self._id))
                    pass
        finally:
            self._logger.info("SERVER({}) terminating".format(self._id))
