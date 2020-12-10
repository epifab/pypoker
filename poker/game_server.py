import logging
import threading
from typing import List, Generator, Dict
from uuid import uuid4

import gevent

from .player_server import PlayerServer
from .game_room import FullGameRoomException, GameRoom, GameRoomFactory


class ConnectedPlayer:
    def __init__(self, player: PlayerServer, room_id: str = None):
        self.player: PlayerServer = player
        self.room_id: str = room_id


class GameServer:
    def __init__(self, room_factory: GameRoomFactory, logger=None):
        self._id: str = str(uuid4())
        self._rooms: List[GameRoom] = []
        self._players: Dict[str, PlayerServer] = {}
        self._lobby_lock = threading.Lock()
        self._room_factory: GameRoomFactory = room_factory
        self._logger = logger if logger else logging

    def __str__(self):
        return "server {}".format(self._id)

    def new_players(self) -> Generator[ConnectedPlayer, None, None]:
        raise NotImplementedError

    def __get_room(self, room_id: str) -> GameRoom:
        try:
            return next(room for room in self._rooms if room.id == room_id)
        except StopIteration:
            room = self._room_factory.create_room(id=room_id, private=True, logger=self._logger)
            self._rooms.append(room)
            return room

    def _join_private_room(self, player: PlayerServer, room_id: str) -> GameRoom:
        self._lobby_lock.acquire()
        try:
            room = self.__get_room(room_id)
            room.join(player)
            return room
        finally:
            self._lobby_lock.release()

    def _join_any_public_room(self, player: PlayerServer) -> GameRoom:
        self._lobby_lock.acquire()
        try:
            # Adding player to the first non-full public room
            for room in self._rooms:
                if not room.private:
                    try:
                        room.join(player)
                        return room
                    except FullGameRoomException:
                        pass

            # All rooms are full: creating new room
            room = self._room_factory.create_room(id=str(uuid4()), private=False, logger=self._logger)
            room.join(player)
            self._rooms.append(room)
            return room
        finally:
            self._lobby_lock.release()

    def _join_room(self, player: ConnectedPlayer) -> GameRoom:
        if player.room_id is None:
            self._logger.info("Player {}: joining public room".format(player.player))
            return self._join_any_public_room(player.player)
        else:
            self._logger.info("Player {}: joining private room {}".format(player.player, player.room_id))
            return self._join_private_room(player.player, player.room_id)

    def start(self):
        self._logger.info("{}: running".format(self))
        self.on_start()
        try:
            for player in self.new_players():
                # Player successfully connected: joining the lobby
                self._logger.info("{}: {} connected".format(self, player.player))
                try:
                    room = self._join_room(player)
                    self._logger.info("Room: {}".format(room.id))
                    if not room.active:
                        room.active = True
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
