from . import Game, ScoreDetector, Deck
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

    def _join_lobby(self, new_player):
        connected = new_player.try_send_message({
            "msg_id": "connect",
            "server": self._id,
            "player": new_player.dto()
        })

        if not connected:
            self._logger.error("{}: Unable to connect {}".format(self, new_player))
            return

        self._lobby_lock.acquire()

        try:
            # Clean-up the lobby
            new_lobby = []
            for player in self._lobby:
                if player.get_id() == new_player.get_id() or not player.ping(pong=True):
                    self._logger.info("{}: {} left the lobby".format(self, player))
                    self._broadcast({"msg_id": "lobby-update", "event": "player-removed", "player": player.dto()})
                    player.disconnect()
                else:
                    new_lobby.append(player)
            self._lobby = new_lobby

            self._lobby.append(new_player)
            self._logger.info("{}: {} has joined the lobby".format(self, new_player))
            self._broadcast({"msg_id": "lobby-update", "event": "player-added", "player": new_player.dto()})

            # Start a new game
            if len(self._lobby) >= self._room_size:
                lowest_rank = 11 - len(self._lobby)
                game = Game(players=self._lobby,
                            deck=Deck(lowest_rank),
                            score_detector=ScoreDetector(lowest_rank),
                            stake=10.0,
                            logger=self._logger)
                # Subscribe all players to game events
                for new_player in self._lobby:
                    game.subscribe(new_player)
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
        self.on_start()
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
            self.on_shutdown()

    def on_start(self):
        pass

    def on_shutdown(self):
        pass
