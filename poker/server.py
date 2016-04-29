from . import Game, GameError, ScoreDetector, Deck
import logging
import threading
import random
import string


class Server:
    def __init__(self, logger=None):
        self._id = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(5))
        self._lobby = []
        self._room_size = 2
        self._lobby_lock = threading.Lock()
        self._logger = logger if logger else logging

    def __str__(self):
        return "server " + self._id

    def new_players(self):
        raise NotImplementedError

    def _broadcast(self, message):
        for player in self._lobby:
            player.try_send_message(message)

    def _join_lobby(self, player):
        connected = player.try_send_message({
            "msg_id": "connect",
            "server": self._id,
            "player": player.dto()
        })

        if not connected:
            self._logger.error("{}: Unable to connect {}".format(self, player))
            return

        self._lobby_lock.acquire()

        try:
            # Clean-up the lobby
            new_lobby = []

            for p in self._lobby:
                if p.get_id() == player.get_id() or not p.ping():
                    self._logger.info("{}: {} left the lobby".format(self, p))
                    self._broadcast({"msg_id": "lobby-update", "event": "player-removed", "player": p.dto()})
                    p.disconnect()
                else:
                    new_lobby.append(p)

            self._lobby = new_lobby

            self._lobby.append(player)
            self._logger.info("{}: {} has joined the lobby".format(self, player))
            self._broadcast({"msg_id": "lobby-update", "event": "player-added", "player": player.dto()})

            if len(self._lobby) >= self._room_size:
                lowest_rank = 11 - len(self._lobby)
                game = Game(players=self._lobby,
                            deck=Deck(lowest_rank),
                            score_detector=ScoreDetector(lowest_rank),
                            stake=10.0,
                            logger=self._logger)
                thread = threading.Thread(target=Server._play_game, args=(self, game, self._lobby))
                thread.start()
                self._lobby = []
        finally:
            self._lobby_lock.release()

    def _play_game(self, game, players):
        try:
            self._logger.info("{}: starting game {}".format(self, game))

            game.play_game()

            for player in players:
                # Try to send the player a notification
                self._join_lobby(player)
        except:
            # Something terrible happened
            self._logger.exception("{}: unhandled game exception for {}".format(self, game))
            for player in players:
                player.disconnect()
            raise
        finally:
            self._logger.info("{}: terminated {}".format(self, game))

    def start(self):
        self._logger.info("{}: running".format(self))
        try:
            for player in self.new_players():
                try:
                    # Player successfully connected: joining the lobby
                    self._logger.info("{}: {} connected".format(self, player))
                    self._join_lobby(player)
                except:
                    # Close bad connections and ignore the connection
                    self._logger.exception("{}: bad connection".format(self))
                    pass
        finally:
            self._logger.info("{}: terminating".format(self))
