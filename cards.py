import random
import collections


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
        11: "Jack",
        12: "Queen",
        13: "King",
        14: "Ace"}
    SUITS = {
        3: "Hearts",
        2: "Diamonds",
        1: "Clubs",
        0: "Spades"}

    def __init__(self, rank, suit):
        if rank not in Card.RANKS:
            raise ValueError("Invalid card rank")
        if suit not in Card.SUITS:
            raise ValueError("Invalid card suit")
        self._value = (rank << 2) + suit

    def get_rank(self):
        return self._value >> 2

    def get_suit(self):
        return self._value & 3

    def __int__(self):
        return self._value

    def __cmp__(self, other):
        return self._value - other._value

    def __str__(self):
        return str(Card.RANKS[self.get_rank()]) + " of " + Card.SUITS[self.get_suit()]

    def __repr__(self):
        return str(self)


class Score:
    HIGHEST_CARD = 0
    PAIR = 1
    DOUBLE_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FULL_HOUSE = 5
    FLUSH = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    CATEGORIES = {
        0: "Highest Card",
        1: "Pair",
        2: "Double Pair",
        3: "Three of a Kind",
        4: "Straight",
        5: "Full House",
        6: "Flush",
        7: "Four of a Kind",
        8: "Straight Flush"}


class CardSet:
    def __init__(self, cards, lowest_rank=2):
        if len(cards) != 5:
            raise ValueError("Expected set of 5 cards, .")
        self._cards = sorted(cards, key=int, reverse=True)
        self._suits = collections.Counter([card.get_suit() for card in self._cards])
        self._ranks = collections.Counter([card.get_rank() for card in self._cards])
        self._unpaired = sorted([rank for rank in self._ranks if self._ranks[rank] == 1], reverse=True)
        self._pairs = sorted([rank for rank in self._ranks if self._ranks[rank] == 2], reverse=True)
        self._three_oak = [rank for rank in self._ranks if self._ranks[rank] == 3]
        self._four_oak = [rank for rank in self._ranks if self._ranks[rank] == 4]
        # ~~~~~~~~~~~~~~~~~~~
        # Straights detection
        # ~~~~~~~~~~~~~~~~~~~
        self._is_straight = True
        # Note: in a straight the Ace can either go after the King or before the lowest rank card
        straight_start = 2 if self._cards[0].get_rank() == 14 and self._cards[-1].get_rank() == lowest_rank else 1
        for i in range(straight_start, len(self._cards)):
            if self._cards[i].get_rank() != self._cards[i - 1].get_rank() - 1:
                self._is_straight = False
                break
        if self._is_straight and straight_start == 2:
            # Minimum straight detected: move the ace at the end of the sequence
            self._cards.append(self._cards[0])
            del self._cards[0]

    def get_cards(self):
        return self._cards

    def is_straight(self):
        return self._is_straight

    def straight_is_min(self):
        return self._is_straight and self._cards[-1] == 15

    def straight_is_max(self):
        return self._is_straight and self._cards[0] == 15

    def get_unpaired(self):
        return self._unpaired

    def get_pair1_rank(self):
        return None if not self._pairs else self._pairs[0]

    def get_pair2_rank(self):
        return None if len(self._pairs) < 2 else self._pairs[1]

    def get_three_oak_rank(self):
        return None if not self._three_oak else self._three_oak[0]

    def get_four_oak_rank(self):
        return None if not self._four_oak else self._four_oak[0]

    def is_flush(self):
        return len(self._suits) == 1

    def get_score(self):
        if self.is_flush() and self.is_straight():
            return Score.STRAIGHT_FLUSH
        elif self.get_four_oak_rank():
            return Score.FOUR_OF_A_KIND
        elif self.is_flush():
            return Score.FLUSH
        elif self.get_three_oak_rank() and self.get_pair1_rank():
            return Score.FULL_HOUSE
        elif self.is_straight():
            return Score.STRAIGHT
        elif self.get_three_oak_rank():
            return Score.THREE_OF_A_KIND
        elif self.get_pair2_rank():
            return Score.DOUBLE_PAIR
        elif self.get_pair1_rank():
            return Score.PAIR
        else:
            return Score.HIGHEST_CARD

    def __lt__(self, other):
        return self._cmp(other) < 0

    def __eq__(self, other):
        return self._cmp(other) == 0

    def __str__(self):
        return str(self.get_cards()) + "\n" + Score.CATEGORIES[self.get_score()]

    @staticmethod
    def _cmp_cards_ranks(cards1, cards2):
        for i in range(len(cards1)):
            rank_diff = cards1[i].get_rank() - cards2[i].get_rank()
            if rank_diff:
                return rank_diff
        return 0

    @staticmethod
    def _cmp_cards_suits(cards1, cards2):
        for i in range(len(cards1)):
            suit_diff = cards1[i].get_suit() - cards2[i].get_suit()
            if suit_diff:
                return suit_diff
        return 0

    @staticmethod
    def _cmp_cards(cards1, cards2):
        rank_diff = CardSet._cmp_cards_ranks(cards1, cards2)
        if rank_diff != 0:
            return rank_diff
        return CardSet._cmp_cards_suits(cards1, cards2)

    def _cmp(self, other):
        score_diff = self.get_score() - other.get_score()
        if score_diff:
            return score_diff
        cmp_methods = {
            Score.HIGHEST_CARD: self._cmp_highest_card,
            Score.PAIR: self._cmp_pair,
            Score.DOUBLE_PAIR: self._cmp_double_pair,
            Score.THREE_OF_A_KIND: self._cmp_three_oak,
            Score.STRAIGHT: self._cmp_straight,
            Score.FULL_HOUSE: self._cmp_full_house,
            Score.FLUSH: self._cmp_flush,
            Score.FOUR_OF_A_KIND: self._cmp_four_oak,
            Score.STRAIGHT_FLUSH: self._cmp_straight_flush
        }
        return cmp_methods[self.get_score()](other)

    def _cmp_highest_card(self, other):
        return CardSet._cmp_cards(self.get_cards(), other.get_cards())

    def _cmp_pair(self, other):
        rank_diff = self.get_pair1_rank() - other.get_pair1_rank()
        if rank_diff:
            return rank_diff
        return CardSet._cmp_cards(self.get_unpaired(), other.get_unpaired())

    def _cmp_double_pair(self, other):
        rank_diff = self.get_pair1_rank() - other.get_pair1_rank()
        if rank_diff:
            return rank_diff
        rank_diff = self.get_pair2_rank() - other.get_pair2_rank()
        if rank_diff:
            return rank_diff
        return CardSet._cmp_cards(self.get_unpaired(), other.get_unpaired())

    def _cmp_three_oak(self, other):
        return self.get_three_oak_rank() - other.get_three_oak_rank()

    def _cmp_straight(self, other):
        return CardSet._cmp_cards([self.get_cards()[0]], [other.get_cards()[0]])

    def _cmp_full_house(self, other):
        return self._cmp_three_oak(other)

    def _cmp_flush(self, other):
        return self._cmp_highest_card(other)

    def _cmp_four_oak(self, other):
        return self.get_four_oak_rank() - other.get_four_oak_rank()

    def _cmp_straight_flush(self, other):
        # Min straight flush is stronger than royal flush
        if self.straight_is_max() and other.straight_is_min():
            return -1
        elif self.straight_is_min() and other.straight_is_max():
            return 1
        return self._cmp_straight(other)

