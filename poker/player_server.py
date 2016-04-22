from . import Player, MessageFormatError, ChannelError, MessageTimeout
import logging
import time


class PlayerServer(Player):
    def __init__(self, channel, id, name, money, logger=None):
        Player.__init__(self, id=id, name=name, money=money)
        self.channel = channel
        self._logger = logger if logger else logging

    def dto(self, with_score=False):
        return {
            "id": self.get_id(),
            "name": self.get_name(),
            "money": self.get_money(),
            "score": self.get_score().dto() if with_score else None}

    def disconnect(self):
        """Disconnect the client"""
        try:
            self.channel.close()
        except:
            pass

    def set_cards(self, cards, score):
        """Assigns a list of cards to the player"""
        Player.set_cards(self, cards, score)

        self.send_message({
            "msg_id": "set-cards",
            "cards": [c.dto() for c in self._cards],
            "score": self.get_score().dto()})

    def change_cards(self, timeout=None):
        """Gives players the opportunity to change some of their cards.
        Returns a tuple: (discard card ids, discards)."""
        self.send_message({
            "msg_id": "change-cards",
            "timeout": None if not timeout else time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout))})

        message = self.recv_message(timeout=timeout)

        MessageFormatError.validate_msg_id(message, "change-cards")

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

    def bet(self, min_bet=0.0, max_bet=0.0, opening=False, timeout=None):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        self.send_message({
            "msg_id": "bet",
            "timeout": None if not timeout else time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout)),
            "min_bet": min_bet,
            "max_bet": max_bet,
            "opening": opening})

        message = self.recv_message(timeout=timeout)

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
            raise MessageFormatError(attribute="bet", desc="'{}' is not a number".format(message.bet))

    def try_send_message(self, message):
        try:
            self.send_message(message)
            return True
        except ChannelError as e:
            return False

    def send_message(self, message):
        return self.channel.send_message(message)

    def recv_message(self, timeout=None):
        return self.channel.recv_message(timeout)
