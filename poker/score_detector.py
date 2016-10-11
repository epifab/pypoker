import collections


class Cards:
    def __init__(self, cards, lowest_rank=2):
        # Sort the list of cards in a descending order
        self._sorted = sorted(cards, key=int, reverse=True)
        self._lowest_rank = lowest_rank

    def _group_by_ranks(self):
        # Group cards by their ranks.
        # Returns a dictionary keyed by rank and valued by list of cards with the same rank.
        # Each list is sorted by card values in a descending order.
        ranks = collections.defaultdict(list)
        for card in self._sorted:
            ranks[card.rank].append(card)
        return ranks

    def _x_sorted_list(self, x):
        """
        If x = 2 returns a list of pairs, if 3 a list of trips, ...
        The list is sorted by sublist ranks.
        If x = 2 and there is a pair of J and a pair of K, the pair of K will be the first element of the list.
        Every sublist is sorted by card suit.
        If x = 4 and the there is a quads of A's, then the quad will be sorted: A of hearts, A of diamonds, ...
        :param x: dimension of every sublist
        :return: a list of a list of cards
        """
        return sorted(
            (cards for cards in self._group_by_ranks().values() if len(cards) == x),
            key=lambda cards: cards[0].rank,
            reverse=True
        )

    def _get_straight(self, sorted_cards):
        if len(sorted_cards) < 5:
            return None

        straight = [sorted_cards[0]]

        for i in range(1, len(sorted_cards)):
            if sorted_cards[i].rank == sorted_cards[i - 1].rank - 1:
                straight.append(sorted_cards[i])
                if len(straight) == 5:
                    return straight
            elif sorted_cards[i].rank != sorted_cards[i - 1].rank:
                straight = [sorted_cards[i]]

        # The Ace can go under the lowest rank card
        if len(straight) == 4 and sorted_cards[0].rank == 14 and straight[-1].rank == self._lowest_rank:
            straight.append(sorted_cards[0])
            return straight
        return None

    def _merge_with_cards(self, score_cards):
        return score_cards + [card for card in self._sorted if card not in score_cards]

    def quads(self):
        quads_list = self._x_sorted_list(4)
        try:
            return self._merge_with_cards(quads_list[0])
        except IndexError:
            return None

    def full_house(self):
        trips_list = self._x_sorted_list(3)
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(trips_list[0] + pair_list[0])
        except IndexError:
            return None

    def trips(self):
        trips_list = self._x_sorted_list(3)
        try:
            return self._merge_with_cards(trips_list[0])
        except IndexError:
            return None

    def two_pair(self):
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(pair_list[0] + pair_list[1])
        except IndexError:
            return None

    def pair(self):
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(pair_list[0])
        except IndexError:
            return None

    def straight(self):
        straight = self._get_straight(self._sorted)
        if straight:
            return self._merge_with_cards(straight)
        else:
            return None

    def flush(self):
        suits = collections.defaultdict(list)
        for card in self._sorted:
            suits[card.suit].append(card)
            # Since cards is sorted, the first flush detected is guaranteed to be the highest one
            if len(suits[card.suit]) == 5:
                return self._merge_with_cards(suits[card.suit])
        return None

    def straight_flush(self):
        suits = collections.defaultdict(list)
        for card in self._sorted:
            suits[card.suit].append(card)
            if len(suits[card.suit]) >= 5:
                straight = self._get_straight(suits[card.suit])
                # Since cards is sorted, the first straight flush detected is guaranteed to be the highest one
                if straight:
                    return self._merge_with_cards(straight)
        return None

    def no_pair(self):
        return self._sorted


class Score:
    def __init__(self, category, cards):
        self._category = category
        self._cards = cards

    @property
    def category(self):
        """Gets the category for this score."""
        return self._category

    @property
    def cards(self, limit=0):
        return self._cards

    def cmp(self, other):
        raise NotImplemented

    @staticmethod
    def _cmp_cards(cards1, cards2):
        """Compare two list of cards according to ranks and suits."""
        rank_diff = Score._cmp_ranks(cards1, cards2)
        if rank_diff:
            return rank_diff
        return Score._cmp_suits(cards1, cards2)

    @staticmethod
    def _cmp_ranks(cards1, cards2):
        """Compare two list of cards ranks.
        Returns a negative integer if cards1 < cards2, positive if cards1 > cards2 or 0 if their ranks are identical"""
        for i in range(len(cards1)):
            try:
                rank_diff = cards1[i].rank - cards2[i].rank
                if rank_diff:
                    return rank_diff
            except IndexError:
                # cards1 is longer than cards2
                return 1
        return 0 if len(cards1) == len(cards2) else -1 # cards2 is longer than cards1

    @staticmethod
    def _cmp_suits(cards1, cards2):
        """Compare two list of cards suits.
        Returns a negative integer if cards1 < cards2, positive if cards1 > cards2 or 0 if their suits are identical"""
        for i in range(len(cards1)):
            try:
                suit_diff = cards1[i].suit - cards2[i].suit
                if suit_diff:
                    return suit_diff
            except IndexError:
                # cards1 is longer than cards2
                return 1
        return 0 if len(cards1) == len(cards2) else -1  # cards2 is longer than cards1

    def dto(self):
        return {
            "category": self.category,
            "cards": [card.dto() for card in self.cards]
        }


class TraditionalPokerScore(Score):
    NO_PAIR = 0
    PAIR = 1
    TWO_PAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FULL_HOUSE = 5
    FLUSH = 6
    QUADS = 7
    STRAIGHT_FLUSH = 8
    
    def cmp(self, other):
        # Compare categories first
        categories_diff = self.category - other.category
        if categories_diff:
            return categories_diff

        # Same score, compare the list of cards
        cards1 = self.cards[0:5]
        cards2 = other.cards[0:5]

        # In a traditional poker, royal flushes are weaker than minimum straight flushes
        # This is done so you are not mathematically sure to have the strongest hand.
        if self.category == TraditionalPokerScore.STRAIGHT_FLUSH:
            if TraditionalPokerScore._straight_is_max(cards1) and TraditionalPokerScore._straight_is_min(cards2):
                return -1
            elif TraditionalPokerScore._straight_is_min(cards1) and TraditionalPokerScore._straight_is_max(cards2):
                return 1

        return Score._cmp_cards(cards1, cards2)

    @staticmethod
    def _straight_is_min(straight_sequence):
        return straight_sequence[4].rank == 14

    @staticmethod
    def _straight_is_max(straight_sequence):
        return straight_sequence[0].rank == 14


class HoldemPokerScore(Score):
    NO_PAIR = 0
    PAIR = 1
    TWO_PAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    QUADS = 7
    STRAIGHT_FLUSH = 8

    def cmp(self, other):
        # Compare categories first
        categories_diff = self.category - other.category
        if categories_diff:
            return categories_diff

        # Same score, compare the list of cards
        cards1 = self.cards[0:5]
        cards2 = other.cards[0:5]

        return Score._cmp_ranks(cards1, cards2)


class ScoreDetector:
    def get_score(self, cards):
        raise NotImplemented


class TraditionalPokerScoreDetector(ScoreDetector):
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank

    def get_score(self, cards):
        cards = Cards(cards, self._lowest_rank)

        score_functions = [
            (TraditionalPokerScore.STRAIGHT_FLUSH,  cards.straight_flush),
            (TraditionalPokerScore.QUADS,           cards.quads),
            (TraditionalPokerScore.FLUSH,           cards.flush),
            (TraditionalPokerScore.FULL_HOUSE,      cards.full_house),
            (TraditionalPokerScore.STRAIGHT,        cards.straight),
            (TraditionalPokerScore.TRIPS,           cards.trips),
            (TraditionalPokerScore.TWO_PAIR,        cards.two_pair),
            (TraditionalPokerScore.PAIR,            cards.pair),
            (TraditionalPokerScore.NO_PAIR,         cards.no_pair),
        ]

        for score_category, score_function in score_functions:
            score = score_function()
            if score:
                return TraditionalPokerScore(score_category, score)

        raise RuntimeError("Unable to detect the score")


class HoldemPokerScoreDetector(ScoreDetector):
    def get_score(self, cards):
        cards = Cards(cards, 2)
        score_functions = [
            (HoldemPokerScore.STRAIGHT_FLUSH,   cards.straight_flush),
            (HoldemPokerScore.QUADS,            cards.quads),
            (HoldemPokerScore.FULL_HOUSE,       cards.full_house),
            (HoldemPokerScore.FLUSH,            cards.flush),
            (HoldemPokerScore.STRAIGHT,         cards.straight),
            (HoldemPokerScore.TRIPS,            cards.trips),
            (HoldemPokerScore.TWO_PAIR,         cards.two_pair),
            (HoldemPokerScore.PAIR,             cards.pair),
            (HoldemPokerScore.NO_PAIR,          cards.no_pair),
        ]

        for score_category, score_function in score_functions:
            score = score_function()
            if score:
                return HoldemPokerScore(score_category, score)

        raise RuntimeError("Unable to detect the score")
