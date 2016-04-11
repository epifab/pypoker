from poker import *
import logging
import socket
import sys
import time
import os
import calendar


class PlayerConsole(Player):
    def __init__(self, id, name, money):
        Player.__init__(self, id, name, money)

    @staticmethod
    def input(timeout, question=""):
        # @todo: Implement non blocking IO (with timeout)
        print("{:.0f} seconds remaining".format(round(timeout)))
        return input(question)

    def discard_cards(self, timeout_epoch):
        """Gives players the opportunity to discard some of their cards.
        Returns a tuple: (remaining cards, discards)."""
        print(str(self))
        print(Card.format_cards(self._cards))

        while True:
            try:
                discard_keys = PlayerConsole.input(
                    timeout_epoch - time.time(),
                    "Please type a comma separated list of card (1 to 5 from left to right): ")
                if discard_keys:
                    # Convert the string into a list of unique integers
                    discard_keys = [int(card_id.strip()) - 1 for card_id in discard_keys.split(",")]
                    if len(discard_keys) > 4:
                        print("You cannot change more than 4 cards")
                        continue
                    # Works out the new card set
                    discards = [self._cards[key] for key in discard_keys]
                    remaining_cards = [self._cards[key] for key in range(len(self._cards)) if key not in discard_keys]
                    return discard_keys, discards
                return [], []
            except TimeoutError:
                return [], []
            except (ValueError, IndexError):
                print("One or more invalid card id.")

    def bet(self, min_bet, max_bet, opening, timeout_epoch):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        print(str(self))
        print(str(self._score))

        if max_bet == -1:
            try:
                PlayerConsole.input(timeout_epoch - time.time(), "Not allowed to open. Press enter to continue.")
            except TimeoutError:
                pass
            finally:
                return -1

        while True:
            message = "Type your bet."
            if min_bet:
                message += " min bet: ${:,.2f}".format(min_bet)
            if max_bet:
                message += " max bet: ${:,.2f}".format(max_bet)
            message += " -1 to " + ("skip opening" if opening else "fold") + ": "

            try:
                bet = PlayerConsole.input(timeout_epoch - time.time(), message)

                bet = float(bet)

                if bet == -1:
                    return -1
                elif bet < min_bet:
                    raise ValueError
                elif max_bet and bet > max_bet:
                    raise ValueError

                self._money -= bet
                return bet

            except TimeoutError:
                print("Timed out")
                return -1
            except (ValueError, TypeError):
                print("Invalid bet.")

    def send_message(self, message):
        """Sends a message to the client."""
        pass

    def recv_message(self):
        """Receives a message to the client."""
        pass

    def __str__(self):
        return "\n" + "{} ${:,.2f}".format(self.get_name(), self.get_money())


class PlayerClientConsole(PlayerConsole):
    def __init__(self, server, name, money):
        PlayerConsole.__init__(self, id=None, name=name, money=money)
        self._server = server
        self._connect()

    def _connect(self):
        self.send_message({
            'msg_id': 'connect',
            'player': {
                'id': self.get_id(),
                'name': self.get_name(),
                'money': self.get_money()}})

        message = self.recv_message()

        MessageFormatError.validate_msg_id(message, "connect")

        try:
            self._id = message['player']['id']
        except IndexError:
            raise MessageFormatError(attribute="player", desc="Missing required information")

    def set_cards(self, cards, score):
        """Assigns a list of cards to the player"""
        PlayerConsole.set_cards(self, cards, score)
        print(str(self))
        print(str(self._score))

    def discard_cards(self, timeout_epoch):
        """Gives players the opportunity to discard some of their cards.
        Returns a list of discarded cards."""
        discard_keys, discards = PlayerConsole.discard_cards(self, timeout_epoch)
        self.send_message({'msg_id': 'discard-cards', 'cards': discard_keys})
        return discard_keys, discards

    def bet(self, min_bet, max_bet, opening, timeout_epoch):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        bet = PlayerConsole.bet(self, min_bet, max_bet, opening, timeout_epoch)
        self.send_message({'msg_id': 'bet', 'bet': bet})

    def try_send_message(self, message):
        try:
            self.send_message(message)
            return True
        except CommunicationError as e:
            self._logger.exception("Player {}: {}".format(self.get_id(), e.args[0]))
            self._error = e
            return False

    def send_message(self, message):
        return self._server.send_message(message)

    def recv_message(self):
        return self._server.recv_message()

    def __str__(self):
        return "\n" + "{} ${:,.2f}".format(self.get_name(), self.get_money())


class GameClientConsole:
    def __init__(self, player):
        self._player = player
    
    def play(self):
        while True:
            message = self._player.recv_message()

            if message["msg_id"] == "game-status":
                if message["status"]:
                    print()
                    print("#" * 80)
                    print()
                    print("NEW GAME")
                    print()
                    print("#" * 80)
                    print()
                else:
                    print()
                    print("#" * 80)
                    print()
                    print("GAME OVER")
                    print()
                    print("#" * 80)
                    print()

            elif message["msg_id"] == "disconnect":
                print()
                print("#" * 80)
                print()
                print("DISCONNECTING")
                print()
                print("#" * 80)
                print()
                break

            elif message["msg_id"] == "game-update":
                self._print_game_update(message)

            elif message["msg_id"] == "bet":
                try:
                    timeout_epoch = int(calendar.timegm(time.strptime(message["timeout"], "%Y-%m-%d %H:%M:%S+0000")))
                    self._player.bet(
                        min_bet=message["min_bet"],
                        max_bet=message["max_bet"],
                        opening=message["opening"],
                        timeout_epoch=timeout_epoch)
                except TimeoutError:
                    print("Time is up!")

            elif message["msg_id"] == "set-cards":
                self._player.set_cards(
                    [Card(rank, suit) for rank, suit in message["cards"]],
                    Score(
                        message["score"]["category"],
                        [Card(rank, suit) for rank, suit in message["score"]["cards"]]))

            elif message["msg_id"] == "discard-cards":
                try:
                    timeout_epoch = int(calendar.timegm(time.strptime(message["timeout"], "%Y-%m-%d %H:%M:%S+0000")))
                    self._player.discard_cards(timeout_epoch)
                except TimeoutError:
                    print("Time is up!")

    def _print_game_update(self, message):
        print()
        print("~" * 45)

        if message["phase"] == Game.PHASE_CARDS_ASSIGNMENT:
            for player in message["players"]:
                print("Player '{}'\n Cash: ${:,.2f}\n Bets: ${:,.2f}".format(
                    player["name"],
                    player["money"],
                    player["bet"]))

                if player["id"] == self._player.get_id():
                    print(Card.format_cards(self._player.get_score().get_cards()))
                    self._player.set_money(player["money"])
                else:
                    print("+-------+" * 5)
                    print("| ///// |" * 5)
                    print("| ///// |" * 5)
                    print("| ///// |" * 5)
                    print("| ///// |" * 5)
                    print("| ///// |" * 5)
                    print("+-------+" * 5)

        elif message["phase"] == Game.PHASE_OPENING_BET or message["phase"] == Game.PHASE_FINAL_BET:
            player_name = message["players"][message["player"]]["name"]
            if message["bet_type"] == "RAISE":
                print("Player '{}' bet ${:,.2f} RAISE".format(player_name, message["bet"], message["bet_type"]))
            else:
                print("Player '{}' {}".format(player_name, message["bet_type"]))

        elif message["phase"] == Game.PHASE_CARDS_CHANGE:
            player_name = message["players"][message["player"]]["name"]
            print("Player '{}' changed {} cards".format(player_name, message["num_cards"]))

        elif message["phase"] == Game.PHASE_SHOW_CARDS:
            player_name = message["players"][message["player"]]["name"]
            if not message["score"]:
                print("Player '{}' FOLD".format(player_name))
            else:
                score = Score(
                    message["score"]["category"],
                    [Card(rank, suit) for (rank, suit) in message["score"]["cards"]])
                print("Player '{}' score:".format(player_name))
                print(str(score))

        elif message["phase"] == Game.PHASE_WINNER_DESIGNATION:
            player_name = message["players"][message["player"]]["name"]
            print()
            print("~" * 45)
            print("Player '{}' WON!!!".format(player_name))
            print("~" * 45)
            print()

        print()
        print("Pot: ${:,.2f}".format(message["pot"]))
        print("~" * 45)
        print()
        print("Waiting...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger()

    player_name = sys.argv[1]

    host = "localhost" if "POKER5_HOST" not in os.environ else os.environ["POKER5_HOST"]
    port = 9000 if "POKER5_PORT" not in os.environ else os.environ["POKER5_PORT"]
    server_address = (host, port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logger.info("Connection established with the Poker5 server at {}".format(server_address))

    player = PlayerClientConsole(JsonSocket(socket=sock, address=server_address), name=player_name, money=1000)
    game = GameClientConsole(player)

    logger.info("Player {} '{}' ${:,.2f} CONNECTED".format(player.get_id(), player.get_name(), player.get_money()))

    try:
        game.play()
    finally:
        sock.close()
        logger.info("Poker5 server at {}: connection closed".format(server_address))
