class Card:
    RANKS = {
        2: "2",
        3: "3",
        4: "4",
        5: "5",
        6: "6",
        7: "7",
        8: "8",
        9: "9",
        10: "10",
        11: "J",
        12: "Q",
        13: "K",
        14: "A"}
    SUITS = {
        3: chr(3),  # Hearts
        2: chr(4),  # Diamonds
        1: chr(5),  # Clubs
        0: chr(6)}  # Spades

    def __init__(self, rank, suit):
        if rank not in Card.RANKS:
            raise ValueError("Invalid card rank")
        if suit not in Card.SUITS:
            raise ValueError("Invalid card suit")
        self._value = (rank << 2) + suit

    def get_rank(self):
        """Card rank"""
        return self._value >> 2

    def get_suit(self):
        """Card suit"""
        return self._value & 3

    def __lt__(self, other):
        return int(self) < int(other)

    def __eq__(self, other):
        return int(self) == int(other)

    def __repr__(self):
        return str(Card.RANKS[self.get_rank()]) + " of " + Card.SUITS[self.get_suit()]

    def __int__(self):
        return self._value
