import unittest
import mock
from poker import Player, GameServer
import time


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
        def new_players(self):
            for i in range(500):
                yield GameServerTest.PlayerServerMock(
                    id="player-{}".format(i),
                    name="Player {}".format(i),
                    money=1000.0
                )
            raise StopIteration

    def test_500_players_connection(self):
        time_start = time.time()
        server = GameServerTest.GameServerStub(mock.Mock())
        server.start()
        time_diff = time.time() - time_start
        self.assertLess(time_diff, 0.2, "It took {} seconds to connect 500 players. Too slow!".format(time_diff))


if __name__ == '__main__':
    unittest.main()
