from . import Player, MessageFormatError, SocketError, MessageTimeout
import logging
import time


class PlayerServer(Player):
    USER_ACTION_TIMEOUT = 30

    def __init__(self, client, logger=None):
        Player.__init__(self, id=id(self), name=None, money=None)
        self._error = None
        self._client = client
        self._logger = logger if logger else logging

    def get_error(self):
        return self._error

    def connect(self):
        """Connects the player"""
        message = self.recv_message()

        MessageFormatError.validate_msg_id(message, "connect")

        try:
            self._name = str(message["player"]["name"])
        except IndexError:
            raise MessageFormatError(attribute="player.name", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.name", desc="Invalid player name")

        try:
            self._money = float(message["player"]["money"])
        except IndexError:
            raise MessageFormatError(attribute="player.money", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.money",
                                     desc="'{}' is not a number".format(message["player"]["money"]))

        self.send_message({
            "msg_id": "connect",
            "player": {
                "id": self._id,
                "name": self._name,
                "money": self._money}})

    def disconnect(self):
        """Disconnect the client"""
        try:
            self.try_send_message({"msg_id": "disconnect"})
            self._client.close()
            return True
        except:
            return False

    def set_cards(self, cards, score):
        """Assigns a list of cards to the player"""
        try:
            Player.set_cards(self, cards, score)

            self.send_message({
                "msg_id": "set-cards",
                "cards": [(c.get_rank(), c.get_suit()) for c in self._cards],
                "score": {
                    "category": self.get_score().get_category(),
                    "cards": [(c.get_rank(), c.get_suit()) for c in self.get_score().get_cards()]}})

        except SocketError as e:
            self._logger.exception("Player {} {}: {}".format(self.get_id(), self._client.get_address(), e.args[0]))
            self._error = e

    def discard_cards(self):
        """Gives players the opportunity to discard some of their cards.
        Returns a tuple: (discard card ids, discards)."""
        try:
            time_timeout = time.gmtime(time.time() + PlayerServer.USER_ACTION_TIMEOUT)

            self.send_message({
                "msg_id": "discard-cards",
                "timeout": time.strftime("%Y-%m-%d %H:%M:%S+0000", time_timeout)})

            message = self.recv_message(PlayerServer.USER_ACTION_TIMEOUT)

            MessageFormatError.validate_msg_id(message, "discard-cards")

            if "cards" not in message:
                raise MessageFormatError(attribute="cards", desc="Attribute is missing")

            discard_keys = message["cards"]

            try:
                # removing duplicates
                discard_keys = sorted(set(discard_keys))
                if len(discard_keys) > 4:
                    raise MessageFormatError(attribute="cards", desc="Maximum number of cards exceeded")
                discards = [self._cards[key] for key in discard_keys]
                return discard_keys, discards

            except (TypeError, IndexError):
                raise MessageFormatError(attribute="cards", desc="Invalid list of cards")

        except (SocketError, MessageFormatError, MessageTimeout) as e:
            self._logger.exception("Player {} {}: {}".format(self.get_id(), self._client.get_address(), e.args[0]))
            self._error = e
            return self._cards, []

    def bet(self, min_bet=0.0, max_bet=0.0, opening=False):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""

        try:
            time_timeout = time.gmtime(time.time() + PlayerServer.USER_ACTION_TIMEOUT)

            self.send_message({
                "msg_id": "bet",
                "timeout": time.strftime("%Y-%m-%d %H:%M:%S+0000", time_timeout),
                "min_bet": min_bet,
                "max_bet": max_bet,
                "opening": opening})

            message = self.recv_message(PlayerServer.USER_ACTION_TIMEOUT)

            MessageFormatError.validate_msg_id(message, "bet")

            # No bet actually required (opening phase, score is too weak)
            if max_bet == -1:
                return -1

            if "bet" not in message:
                raise MessageFormatError(attribute="bet", desc="Attribute is missing")

            try:
                bet = float(message["bet"])

                # Fold
                if bet == -1.0:
                    return bet

                # Bet range
                if bet < min_bet or bet > max_bet:
                    raise MessageFormatError(
                        attribute="bet",
                        desc="Bet out of range. min: {} max: {}, actual: {}".format(min_bet, max_bet, bet))

                return bet

            except ValueError:
                raise MessageFormatError(attribute="bet", desc="'{}' is not a number".format(bet))

        except (SocketError, MessageFormatError, MessageTimeout) as e:
            self._logger.exception("Player {} {}: {}".format(self.get_id(), self._client.get_address(), e.args[0]))
            self._error = e
            return -1

    def try_send_message(self, message):
        try:
            self.send_message(message)
            return True
        except SocketError as e:
            self._logger.exception("Player {} {}: {}".format(self.get_id(), self._client.get_address(), e.args[0]))
            self._error = e
            return False

    def send_message(self, message):
        return self._client.send_message(message)

    def recv_message(self, timeout=5.0):
        return self._client.recv_message(timeout)
