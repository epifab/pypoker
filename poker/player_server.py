from poker import Player
import logging


class PlayerServer(Player):
    def __init__(self, client):
        Player.__init__(self, name=None, money=None)
        self._client = client
        self._connect()

    def _connect(self):
        message = self.recv_message()
        Player.check_msg_id(message, 'connect')
        self._name = message['player']['name']
        self._money = message['player']['money']
        self.send_message({'msg_id': 'connect', 'player': {'name': self.get_name(), 'money': self.get_money()}})

    def set_cards(self, cards, score):
        """Assigns a list of cards to the player"""
        Player.set_cards(self, cards, score)
        self.send_message({
            'msg_id': 'set-cards',
            'cards': [(c.get_rank(), c.get_suit()) for c in self._cards],
            'score': {
                'category': self.get_score().get_category(),
                'cards': [(c.get_rank(), c.get_suit()) for c in self.get_score().get_cards()]
            }
        })

    def discard_cards(self):
        """Gives players the opportunity to discard some of their cards.
        Returns a tuple: (remaining cards, discards)."""
        self.send_message({
            'msg_id': 'discard-cards'
        })
        message = self.recv_message()
        Player.check_msg_id(message, 'discard-cards')
        discard_keys = message['cards']

        if len(discard_keys) > 4:
            logging.error("Player '{}': attempted to change more than 4 cards".format(self.get_name()))
            self.send_message({'msg_id': 'error', 'error': 'Attempted to change more than 4 cards'})
            return self._cards, []

        try:
            discards = [self._cards[key] for key in discard_keys]
            remaining_cards = [self._cards[key] for key in range(len(self._cards)) if key not in discard_keys]
            return remaining_cards, discards
        except KeyError:
            logging.error("Player '{}': invalid card IDs detected when changing cards")
            self.send_message({'msg_id': 'error', 'error': 'Invalid card IDs'})
            return self._cards, []

    def bet(self, min_bet=0.0, max_bet=0.0, opening=False):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        self.send_message({
            'msg_id': 'bet',
            'min_bet': min_bet,
            'max_bet': max_bet,
            'opening': opening
        })
        message = self.recv_message()
        Player.check_msg_id(message, 'bet')
        try:
            bet = float(message['bet'])
            if max_bet != -1 and (bet < min_bet or bet > max_bet):
                raise ValueError
            return bet
        except ValueError:
            logging.error("Player '{}': invalid bet received")
            return -1

    def send_message(self, message):
        return self._client.send_message(message)

    def recv_message(self):
        return self._client.recv_message()

