from . import Deck, ScoreDetector, Game
import logging
import threading


class FullGameRoomException(Exception):
    pass


class GameRoom(Game.EventListener):
    room_number = 1

    def __init__(self, id, max_room_size=5, stakes=10.0, logger=None):
        self._id = id
        self._max_room_size = max_room_size
        self._stakes = stakes
        self._room_lock = threading.Lock()
        self._players = {}
        self._player_ids = [None] * max_room_size
        self._active = False
        self._logger = logger if logger else logging
        self._last_broadcast_event = None

    def __str__(self):
        return "room {}".format(self._id)

    def _get_free_seat(self):
        try:
            return self._player_ids.index(None)
        except ValueError:
            raise FullGameRoomException

    def join(self, player):
        self._room_lock.acquire()
        try:
            try:
                old_player = self._players[player.get_id()]
                old_player.disconnect()
                # The player was already connected to this room
                # @todo: he could potentially continue to play like he never left
                self._logger.info("{}: {} re-joined".format(self, player))
            except KeyError:
                # new player
                self._player_ids[self._get_free_seat()] = player.get_id()
                self._logger.info("{}: {} joined".format(self, player))
            self._players[player.get_id()] = player
        finally:
            self._room_lock.release()

        if self._last_broadcast_event:
            player.try_send_message(self._last_broadcast_event)

    def leave(self, player_id):
        self._room_lock.acquire()
        try:
            try:
                player = self._players[player_id]
                player.disconnect()
                del self._players[player_id]
                player_key = self._player_ids.index(player_id)
                self._player_ids[player_key] = None
                self._logger.info("{}: {} left".format(self, player))
            except KeyError:
                # Player wasn't actually in the room
                pass
        finally:
            self._room_lock.release()

    def game_event(self, event, event_data, game_data):
        if event == Game.Event.dead_player:
            self.leave(event_data["player_id"])
        # Broadcast the event to the room
        message = {"msg_id": "game-update"}
        message.update(event_data)
        message.update(game_data)
        for player_id in self._players:
            self._players[player_id].try_send_message(message)

        self._last_broadcast_event = None if event == Game.Event.game_over else message

    @property
    def active(self):
        return self._active

    def ping_all_players(self):
        for player_id in self._players.keys():
            if not self._players[player_id].ping():
                self.leave(player_id)

    def activate(self):
        self._active = True
        self._logger.info("{}: active".format(self))
        while self._active:
            # Remove unresponsive players
            self.ping_all_players()

            # List of players sorted according to the original _player_ids list
            players = [self._players[player_id]
                       for player_id in self._player_ids
                       if player_id is not None]

            if len(players) > 1:
                lowest_rank = 11 - len(players)
                game = Game(
                    players=players,
                    deck=Deck(lowest_rank),
                    score_detector=ScoreDetector(lowest_rank),
                    stake=10.0,
                    logger=self._logger
                )
                # Handle game events
                game.subscribe(self)
                game.play_game()
            else:
                self._active = False

        self._logger.info("{}: inactive".format(self))
