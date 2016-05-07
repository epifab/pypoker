class Player:
    def __init__(self, id, name, money):
        self._id = id
        self._name = name
        self._money = money
        self._cards = None
        self._score = None
        self._allowed_to_open = False

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

    def is_allowed_to_open(self):
        """Whether or not the player is allowed to open in the current game."""
        return self._allowed_to_open

    def set_cards(self, cards, score, min_opening_score=None):
        """Assigns a list of cards to the player"""
        self._cards = cards
        self._score = score
        self._allowed_to_open = not min_opening_score or self.get_score().cmp(min_opening_score) >= 0

    def __str__(self):
        return "player " + self._id
