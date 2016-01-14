class Player:
    def __init__(self, id, name, money):
        self._id = id
        self._name = name
        self._money = money
        self._cards = None
        self._score = None

    def get_id(self):
        """Unique player ID"""
        return self._id

    def get_name(self):
        """Player name"""
        return self._name

    def get_money(self):
        """Player money"""
        return self._money

    def set_money(self, money):
        """Sets player money"""
        self._money = money

    def get_cards(self):
        """Gets the list of cards assigned to the player"""
        return self._cards

    def get_score(self):
        """Gets the player score. Returns a Score object."""
        return self._score

    def set_cards(self, cards, score):
        """Assigns a list of cards to the player"""
        self._cards = cards
        self._score = score

    def discard_cards(self):
        raise NotImplementedError

    def bet(self, min_bet=0.0, max_bet=0.0, opening=False):
        raise NotImplementedError

    def send_message(self, message):
        raise NotImplementedError

    def recv_message(self):
        raise NotImplementedError

    @staticmethod
    def check_msg_id(message, expected_msg_id):
        # Retrieving message id
        msg_id = message['msg_id']
        if msg_id != expected_msg_id:
            raise ValueError("Invalid msg_id. Expected: '{}' received: '{}'.".format(expected_msg_id, msg_id))
