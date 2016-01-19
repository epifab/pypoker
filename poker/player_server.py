import logging
import time
from poker import Player, MessageException


class PlayerServer(Player):
    DEFAULT_TIMEOUT = 5
    USER_ACTION_TIMEOUT = 60

    def __init__(self, client):
        Player.__init__(self, id=id(self), name=None, money=None)
        self._error = None
        self._client = client
        self._connect()

    def _connect(self):
        message = self.recv_message(PlayerServer.DEFAULT_TIMEOUT)

        MessageException.validate_msg_id(message, "connect")

        try:
            self._name = message['player']['name']
            self._money = float(message['player']['money'])
        except IndexError:
            raise MessageException(attribute="player", desc="Missing required information")
        except ValueError:
            raise MessageException(attribute="player.money",
                                   desc="'{}' is not a number".format(message['player']['money']))

        self.send_message({
            'msg_id': 'connect',
            'player': {
                'id': self._id,
                'name': self._name,
                'money': self._money}})

    def set_cards(self, cards, score):
        """Assigns a list of cards to the player"""
        Player.set_cards(self, cards, score)
        try:
            self.send_message({
                'msg_id': 'set-cards',
                'cards': [(c.get_rank(), c.get_suit()) for c in self._cards],
                'score': {
                    'category': self.get_score().get_category(),
                    'cards': [(c.get_rank(), c.get_suit()) for c in self.get_score().get_cards()]}})
        except Exception as e:
            logging.exception('Unable to send the cards to player {}'.format(self._id))
            self._error = e

    def discard_cards(self):
        """Gives players the opportunity to discard some of their cards.
        Returns a tuple: (remaining cards, discards)."""
        try:
            time_timeout = time.gmtime(time.time() + PlayerServer.USER_ACTION_TIMEOUT)
            self.send_message({
                'msg_id': 'discard-cards',
                'timeout': time.strftime('%Y-%m-%d %H:%M:%S', time_timeout)})

            message = self.recv_message(PlayerServer.USER_ACTION_TIMEOUT)

            MessageException.validate_msg_id(message, "discard-cards")

            if "cards" not in message:
                raise MessageException(attribute="cards", desc="Attribute is missing")

            discard_keys = message['cards']

            if len(discard_keys) > 4:
                raise MessageException(attribute="cards", desc="Maximum number of cards exceeded")

            try:
                discards = [self._cards[key] for key in discard_keys]
                remaining_cards = [self._cards[key] for key in range(len(self._cards)) if key not in discard_keys]
                return remaining_cards, discards
            except IndexError:
                raise MessageException(attribute="cards", desc="Invalid list of cards")

        except Exception as e:
            logging.exception("Player {} failed to discard cards".format(self._id))
            self.try_send_message({'msg_id': 'error'})
            self._error = e
            return self._cards, []

    def bet(self, min_bet=0.0, max_bet=0.0, opening=False):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""

        try:
            time_timeout = time.gmtime(time.time() + PlayerServer.USER_ACTION_TIMEOUT)
            self.send_message({
                "msg_id": "bet",
                "timeout": time.strftime("%Y-%m-%d %H:%M:%S", time_timeout),
                "min_bet": min_bet,
                "max_bet": max_bet,
                "opening": opening})

            message = self.recv_message(PlayerServer.USER_ACTION_TIMEOUT)

            MessageException.validate_msg_id(message, "bet")

            # No bet actually required (opening phase, score is too weak)
            if max_bet == -1:
                return -1

            if "bet" not in message:
                raise MessageException(attribute="bet", desc="Attribute is missing")

            try:
                bet = float(message['bet'])

                # Fold
                if bet == -1.0:
                    return bet

                # Bet range
                if bet < min_bet or bet > max_bet:
                    raise MessageException(
                        attribute="bet",
                        desc=" Bet out of range. min: {} max: {}, actual: {}".format(min_bet, max_bet, bet))

                self._money -= bet
                return bet

            except ValueError:
                raise MessageException(attribute="bet", desc="'{}' is not a number".format(bet))

        except Exception as e:
            logging.exception("Player {} failed to bet".format(self._id))
            self.try_send_message({'msg_id': 'error'})
            self._error = e
            return -1

    def try_send_message(self, message):
        try:
            self.send_message(message)
        finally:
            pass

    def get_error(self):
        return self._error

    def try_resume(self):
        """Try to resume a player in error"""
        try:
            time_timeout = time.gmtime(time.time() + PlayerServer.USER_ACTION_TIMEOUT)
            self.send_message({
                'msg_id': 'resume',
                'timeout': time.strftime('%Y-%m-%d %H:%M:%S', time_timeout)})

            message = self.recv_message(PlayerServer.USER_ACTION_TIMEOUT)

            MessageException.validate_msg_id(message, "resume")

            if "resume" not in message or not message["resume"]:
                raise MessageException(attribute="resume", desc="Player {} quit".format(self._id))

            self._error = None
            return True

        except Exception as e:
            logging.exception('Unable to resume player {}'.format(self._id))
            self._error = e
            return False

    def disconnect(self):
        """Disconnect the client"""
        try:
            self._client.close()
        finally:
            pass

    def send_message(self, message):
        return self._client.send_message(message)

    def recv_message(self, timeout=None):
        return self._client.recv_message(timeout)
