import time
import unittest
from typing import Generator
from unittest import mock

from poker.game_server import GameServer, ConnectedPlayer
from poker.player import Player


class GameServerTest(unittest.TestCase):

    class PlayerServerMock(Player):
        def recv_message(self, timeout_epoch):
            return None

        def try_send_message(self, message):
            self.send_message(message)

        def send_message(self, message):
            pass

        def disconnect(self):
            pass

    class GameServerStub(GameServer):
        def new_players(self) -> Generator[ConnectedPlayer, None, None]:
            for i in range(500):
                yield ConnectedPlayer(
                    GameServerTest.PlayerServerMock(
                        id="player-{}".format(i),
                        name="Player {}".format(i),
                        money=1000.0
                    )
                )

    def test_500_players_connection(self):
        time_start = time.time()
        server = GameServerTest.GameServerStub(mock.Mock())
        server.start()
        time_diff = time.time() - time_start
        self.assertLess(time_diff, 0.2, "It took {} seconds to connect 500 players. Too slow!".format(time_diff))


if __name__ == '__main__':
    unittest.main()
