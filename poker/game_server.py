from . import GameRoom, FullGameRoomException
import gevent
import logging
import threading
from uuid import uuid4


class GameServer:
    def __init__(self, game_factory, logger=None):
        self._id = str(uuid4())
        self._rooms = []
        self._players = {}
        self._lobby_lock = threading.Lock()
        self._game_factory = game_factory
        self._logger = logger if logger else logging

    def __str__(self):
        return "server {}".format(self._id)

    def new_players(self):
        raise NotImplementedError

    def _join_room(self, player):
        self._lobby_lock.acquire()
        try:
            # Adding player to the first non-full room
            for room in self._rooms:
                try:
                    room.join(player)
                    return room
                except FullGameRoomException:
                    pass

            room_number = GameRoom.room_number
            room_id = "{}/{}".format(self._id, room_number)

            GameRoom.room_number += 1

            # All rooms are full: creating new room
            room = GameRoom(id=room_id, max_room_size=5, game_factory=self._game_factory, logger=self._logger)
            room.join(player)
            self._rooms.append(room)
            return room
        finally:
            self._lobby_lock.release()

    def start(self):
        self._logger.info("{}: running".format(self))
        self.on_start()
        try:
            for player in self.new_players():
                try:
                    # Player successfully connected: joining the lobby
                    self._logger.info("{}: {} connected".format(self, player))
                    room = self._join_room(player)
                    if not room.active:
                        gevent.spawn(room.activate)
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
