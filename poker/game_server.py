from . import Game, ScoreDetector, Deck
import logging
import threading
from uuid import uuid4


class GameServer:
    def __init__(self, logger=None):
        self._id = str(uuid4())
        self._lobby = []
        self._room_size = 2
        self._lobby_lock = threading.Lock()
        self._logger = logger if logger else logging

    def __str__(self):
        return "server {}".format(self._id)

    def __repr__(self):
        return self._id

    def new_players(self):
        raise NotImplementedError

    def _broadcast(self, message):
        for player in self._lobby:
            player.try_send_message(message)

    def _join_lobby(self, new_player):
        self._lobby_lock.acquire()

        self._logger.info("{}: {} joining the lobby".format(self, new_player))

        try:
            # Clean-up the lobby
            new_lobby = []
            for player in self._lobby:
                if player.get_id() == new_player.get_id():
                    # Player was already in the lobby
                    self._logger.info("{}: {} already in the lobby")
                    # Kill the old session
                    self._broadcast({"msg_id": "lobby-update", "event": "player-removed", "player": player.dto()})
                    player.disconnect()

                self._logger.info("{}: ping to player {}".format(self, player))
                if not player.ping(pong=True):
                    # Unresponsive
                    self._logger.info("{}: {} did not respond: kicked out".format(self, player))
                    # Kill inactive session
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
                thread = threading.Thread(target=GameServer._play_game, args=(self, game, self._lobby))
                thread.start()
                self._lobby = []
        finally:
            self._lobby_lock.release()

    def _play_game(self, game, players):
        try:
            self._logger.info("{}: starting {}".format(self, game))
            game.play_game()
        except:
            self._logger.exception("{}: unhandled game exception for {}".format(self, game))
            raise
        finally:
            self._logger.info("{}: terminated {}".format(self, game))
            # Sending players back to the lobby
            for player in players:
                player.disconnect()

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
