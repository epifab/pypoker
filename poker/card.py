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

    @property
    def rank(self):
        return self._value >> 2

    @property
    def suit(self):
        return self._value & 3

    def __lt__(self, other):
        return int(self) < int(other)

    def __eq__(self, other):
        return int(self) == int(other)

    def __repr__(self):
        return str(Card.RANKS[self.rank]) + " of " + Card.SUITS[self.suit]

    def __int__(self):
        return self._value

    @staticmethod
    def format_cards(cards):
        lines = [""] * 7
        for card in cards:
            lines[0] += "+-------+"
            lines[1] += "| {:<2}    |".format(Card.RANKS[card.rank])
            lines[2] += "|       |"
            lines[3] += "|   {}   |".format(Card.SUITS[card.suit])
            lines[4] += "|       |"
            lines[5] += "|    {:>2} |".format(Card.RANKS[card.rank])
            lines[6] += "+-------+"
        return "\n".join(lines)

    def dto(self):
        return self.rank, self.suit
