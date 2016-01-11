import random

from poker.card import Card


class Deck:
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank
        self._cards = None
        self._discards = None

    def initialize(self):
        """Creates and shuffle cards"""
        self._cards = [Card(rank, suit) for rank in range(self._lowest_rank, 15) for suit in range(0, 4)]
        self._discards = []
        random.shuffle(self._cards)

    def get_cards(self, num_cards=1):
        """Returns and removes cards them from the top of the deck."""
        new_cards = []
        if len(self._cards) < num_cards:
            new_cards = self._cards
            self._cards = self._discards
            self._discards = []
            random.shuffle(self._cards)
        return new_cards + [self._cards.pop() for _ in range(num_cards - len(new_cards))]

    def add_discards(self, discards):
        """Adds discarded cards"""
        self._discards += discards
