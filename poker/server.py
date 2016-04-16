from . import Game, GameError, ScoreDetector, Deck, PlayerServer, MessageFormatError
import logging
import threading


class Server:
    def __init__(self, logger=None):
        self._players = []
        self._room_size = 2
        self._lock = threading.Lock()
        self._logger = logger if logger else logging

    def channels(self):
        raise NotImplementedError

    def join_lobby(self, player):
        self._lock.acquire()
        try:
            self._players.append(player)
            self._logger.info("Player {} has joined the lobby.".format(player.get_id()))

            if len(self._players) >= self._room_size:
                lowest_rank = 11 - len(self._players)
                game = Game(players=self._players,
                            deck=Deck(lowest_rank),
                            score_detector=ScoreDetector(lowest_rank),
                            stake=10.0)
                thread = threading.Thread(target=Server.play_game, args=(self, game, self._players))
                thread.start()
                self._players = []
        finally:
            self._lock.release()

    def play_game(self, game, players):
        try:
            self._logger.info("Starting a new game...")

            for player in players:
                player.send_message({"msg_id": "game-status", "status": 1})

            abort_game = False

            while not abort_game:
                try:
                    game.play_hand()
                    abort_game = game.get_players_in_error()
                except GameError:
                    abort_game = True

            self._logger.info("Aborting the game...")

            for player in players:
                # Try to send the player a notification
                game_status_sent = player.try_send_message({"msg_id": "game-status", "status": 0})

                if player.get_error() or not game_status_sent:
                    player.disconnect()
                else:
                    self.join_lobby(player)
        except:
            # Something terrible happened
            self._logger.exception("Unexpected error happened.")

            for player in players:
                player.disconnect()
            raise

    def connect_player(self, channel):
        message = channel.recv_message()

        MessageFormatError.validate_msg_id(message, "connect")

        try:
            id = str(message["player"]["id"])
        except IndexError:
            raise MessageFormatError(attribute="player.id", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.id", desc="Invalid player id")

        try:
            name = str(message["player"]["name"])
        except IndexError:
            raise MessageFormatError(attribute="player.name", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.name", desc="Invalid player name")

        try:
            money = float(message["player"]["money"])
        except IndexError:
            raise MessageFormatError(attribute="player.money", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.money",
                                     desc="'{}' is not a number".format(message["player"]["money"]))

        player = PlayerServer(channel=channel, id=id, name=name, money=money)

        player.try_send_message({
            'msg_id': 'connect',
            'player': {
                'id': player.get_id(),
                'name': player.get_name(),
                'money': player.get_money()
            }})

        return player

    def start(self):
        for channel in self.channels():
            try:
                player = self.connect_player(channel)
                # Player successfully connected: joining the lobby
                self._logger.info("Player {} '{}' CONNECTED".format(player.get_id(), player.get_name()))
                self.join_lobby(player)
            except:
                # Close bad connections and ignore the connection
                channel.close()
                self._logger.exception("Bad connection")
                pass
