from . import Game, GameError
import gevent
import logging
import threading


class FullGameRoomException(Exception):
    pass


class GameRoom(Game.EventListener):
    room_number = 1

    def __init__(self, id, game_factory, max_room_size=5, logger=None):
        self._id = id
        self._max_room_size = max_room_size
        self._game_factory = game_factory
        self._game = None
        self._game_lock = threading.Lock()
        self._dealer_index = -1
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
            "message_type": "room-update",
            "event": "init",
            "room_id": self._id,
            "players": {k: self._players[k].dto() for k in self._players},
            "player_ids": self._player_ids
        })

    def _broadcast_room_event(self, event, player_id):
        self._broadcast({
            "message_type": "room-update",
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
                old_player = self._players[player.id]

            except KeyError:
                # New player
                is_new_player = True
                # Sending room initialization message
                self._send_room_init(player)
                # Adding player to the room
                self._player_ids[self._get_free_seat()] = player.id
                self._players[player.id] = player
                self._broadcast_room_event("player-added", player.id)
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
                        self._latest_game.init_player_hand(player)
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
        # Updating the latest event message
        self._game_lock.acquire()
        try:
            # Broadcast the event to the room
            event_message = {"message_type": "game-update"}
            event_message.update(event_data)
            event_message.update(game_data)
            self._broadcast(event_message)

            if event == Game.Event.CARDS_ASSIGNMENT:
                self._dealer_index = self._player_ids.index(game_data["dealer_id"])

            if event == Game.Event.GAME_OVER:
                self._latest_game = None
                self._latest_game_event = None
            else:
                self._latest_game = self._game
                self._latest_game_event = event_message
        finally:
            self._game_lock.release()

        if event == Game.Event.DEAD_PLAYER:
            self.leave(event_data["player_id"])

    @property
    def active(self):
        return self._active

    def ping_all_players(self):
        for player_id in self._players.keys():
            if not self._players[player_id].ping():
                self.leave(player_id)

    def new_game(self):
        # Remove unresponsive players
        self.ping_all_players()

        self._players_lock.acquire()
        try:
            if len(self._players) < 2:
                raise GameError("Not enough players")

            else:
                # Dealer
                for i in range(self._max_room_size):
                    self._dealer_index = (self._dealer_index + 1) % self._max_room_size
                    if self._player_ids[self._dealer_index] is not None:
                        break

                return self._game_factory.create_game(
                    players=[self._players[player_id] for player_id in self._player_ids if player_id is not None],
                    dealer_id=self._player_ids[self._dealer_index],
                )

        finally:
            self._players_lock.release()

    def activate(self):
        self._active = True
        self._logger.info("{}: active".format(self))

        while self._active:
            try:
                self._game = self.new_game()
                self._game.subscribe(self)
                self._game.play_game()
                self._game.unsubscribe(self)
                self._game = None
            except GameError:
                self._active = False

        self._logger.info("{}: inactive".format(self))
