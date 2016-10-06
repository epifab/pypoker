from . import Deck, ScoreDetector, Game
import gevent
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
        self._game = None
        self._game_lock = threading.Lock()
        self._latest_game_event = None
        self._latest_game = None
        self._players = {}
        self._players_lock = threading.Lock()
        self._player_ids = [None] * max_room_size
        self._active = False
        self._logger = logger if logger else logging

    def __str__(self):
        return "room {}".format(self._id)

    def _get_free_seat(self):
        try:
            return self._player_ids.index(None)
        except ValueError:
            raise FullGameRoomException

    def _send_room_init(self, player):
        player.send_message({
            "msg_id": "room-update",
            "event": "init",
            "room_id": self._id,
            "players": {k: self._players[k].dto() for k in self._players},
            "player_ids": self._player_ids
        })

    def _broadcast_room_event(self, event, player_id):
        self._broadcast({
            "msg_id": "room-update",
            "event": event,
            "room_id": self._id,
            "players": {k: self._players[k].dto() for k in self._players},
            "player_ids": self._player_ids,
            "player_id": player_id
        })

    def _broadcast(self, message):
        gevent.joinall([
            gevent.spawn(player.send_message, message)
            for player in self._players.values()
        ])

    def join(self, player):
        self._players_lock.acquire()
        try:
            is_new_player = True

            try:
                old_player = self._players[player.get_id()]

            except KeyError:
                # New player
                is_new_player = True
                # Sending room initialization message
                self._send_room_init(player)
                # Adding player to the room
                self._player_ids[self._get_free_seat()] = player.get_id()
                self._players[player.get_id()] = player
                self._broadcast_room_event("player-added", player.get_id())
                self._logger.info("{}: {} joined".format(self, player))

            else:
                # Player already connected to this room
                # In case he is currently in a game, we replace the old channel with the new one
                # so he will magically rejoin the game
                is_new_player = False
                old_player.update_channel(player)
                # Throwing away the new player object
                player = old_player
                self._send_room_init(player)
                self._logger.info("{}: {} re-joined".format(self, player))

            # Updating the client
            self._game_lock.acquire()
            try:
                if self._latest_game_event:
                    player.send_message(self._latest_game_event)
                    if not is_new_player:
                        # Sending cards to the player in case he was already in a game
                        self._latest_game.send_cards(player)
            finally:
                self._game_lock.release()
        finally:
            self._players_lock.release()

    def leave(self, player_id):
        self._players_lock.acquire()
        try:
            try:
                player = self._players[player_id]
            except KeyError:
                # Player wasn't actually in the room
                pass
            else:
                player.disconnect()
                del self._players[player_id]
                player_key = self._player_ids.index(player_id)
                self._player_ids[player_key] = None
                self._logger.info("{}: {} left".format(self, player))
                self._broadcast_room_event("player-removed", player_id)

        finally:
            self._players_lock.release()

    def game_event(self, event, event_data, game_data):
        if event == Game.Event.dead_player:
            self.leave(event_data["player_id"])
        # Broadcast the event to the room
        event_message = {"msg_id": "game-update"}
        event_message.update(event_data)
        event_message.update(game_data)

        # Updating the latest event message
        self._game_lock.acquire()
        try:
            if event == Game.Event.game_over:
                self._latest_game = None
                self._latest_game_event = None
            else:
                self._latest_game = self._game
                self._latest_game_event = event_message
        finally:
            self._game_lock.release()

        self._broadcast(event_message)

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

                self._game = Game(
                    players=players,
                    deck=Deck(lowest_rank),
                    score_detector=ScoreDetector(lowest_rank),
                    stake=10.0,
                    logger=self._logger
                )
                self._game.subscribe(self)
                self._game.play_game()
                self._game.unsubscribe(self)
                self._game = None
            else:
                self._active = False

        self._logger.info("{}: inactive".format(self))
