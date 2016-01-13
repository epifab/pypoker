import collections

from poker import Score


class ScoreDetector:
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank

    def get_score(self, cards):
        score, cards = ScoreDetector._detect_score(cards, self._lowest_rank)
        return Score(score, cards)

    @staticmethod
    def _detect_score(cards, lowest_rank):
        """Detects the highest score in the list of cards.
        Returns a tuple (score, cards) where score is an integer (see Score class) and cards is a list of cards sorted
        according to the score in a descending order.
        For instance, the following list of cards in input:
            [10 of hearts, A of clubs, J of diamonds, 10 of clubs, J of hearts]
        will produce the following output:
            (Score.DOUBLE_PAIR, [J of hearts, J of diamonds, 10 of hearts, 10 of clubs, Aof clubs])"""

        def merge_sequence(sequence1, sequence2): return sequence1 + [c for c in sequence2 if c not in sequence1]

        # Sort the list of cards in a descending order
        cards = sorted(cards, key=int, reverse=True)

        # Straight flush
        straight_flush = ScoreDetector._get_straight_flush(cards, lowest_rank)
        if straight_flush:
            return Score.STRAIGHT_FLUSH, merge_sequence(straight_flush, cards)

        # Makes a dictionary keyed by rank and valued by list of cards of the same rank
        ranks = collections.defaultdict(list)
        for card in cards:
            ranks[card.get_rank()].append(card)

        # List of four of a kind ranks
        four_oak_rank = sorted([rank for (rank, cards) in ranks.items() if len(cards) == 4], reverse=True)

        # Four of a kind
        if four_oak_rank:
            return Score.FOUR_OF_A_KIND, merge_sequence(ranks[four_oak_rank[0]], cards)

        # Flush
        flush = ScoreDetector._get_flush(cards)
        if flush:
            return Score.FLUSH, flush

        # List of three of a kind and pair ranks
        three_oak_ranks = sorted([rank for (rank, cards) in ranks.items() if len(cards) == 3], reverse=True)
        pair_ranks = sorted([rank for (rank, cards) in ranks.items() if len(cards) == 2], reverse=True)

        # Full house
        if three_oak_ranks and pair_ranks:
            return Score.FULL_HOUSE, merge_sequence(ranks[three_oak_ranks[0]] + ranks[pair_ranks[0]], cards)

        # Straight
        straight = ScoreDetector._get_straight(cards, lowest_rank)
        if straight:
            return Score.STRAIGHT, merge_sequence(straight, cards)

        # Three of a kind
        if three_oak_ranks:
            return Score.THREE_OF_A_KIND, merge_sequence(ranks[three_oak_ranks[0]], cards)

        # Double pair
        if len(pair_ranks) > 1:
            return Score.DOUBLE_PAIR, merge_sequence(ranks[pair_ranks[0]] + ranks[pair_ranks[1]], cards)

        # Pair
        if pair_ranks:
            return Score.PAIR, merge_sequence(ranks[pair_ranks[0]], cards)

        return Score.HIGHEST_CARD, cards

    @staticmethod
    def _get_straight(cards, lowest_rank):
        """Detects and returns the highest straight from a list of cards sorted in a descending order."""
        if len(cards) < 5:
            return None

        straight = [cards[0]]

        for i in range(1, len(cards)):
            if cards[i].get_rank() == cards[i - 1].get_rank() - 1:
                straight.append(cards[i])
                if len(straight) == 5:
                    return straight
            elif cards[i].get_rank() != cards[i - 1].get_rank():
                straight = [cards[i]]

        # The Ace can go under the lowest rank card
        if len(straight) == 4 and cards[0].get_rank() == 14 and straight[-1].get_rank() == lowest_rank:
            straight.append(cards[0])
            return straight
        return None

    @staticmethod
    def _get_flush(cards):
        """Detects and returns the highest flush from a list of cards sorted in a descending order."""
        suits = collections.defaultdict(list)
        for card in cards:
            suits[card.get_suit()].append(card)
            # Since cards is sorted, the first flush detected is guaranteed to be the highest one
            if len(suits[card.get_suit()]) == 5:
                return suits[card.get_suit()]
        return None

    @staticmethod
    def _get_straight_flush(cards, lowest_rank):
        """Detects and returns the highest straight flush from a list of cards sorted by rank in a descending order."""
        suits = collections.defaultdict(list)
        for card in cards:
            suits[card.get_suit()].append(card)
            if len(suits[card.get_suit()]) >= 5:
                straight = ScoreDetector._get_straight(suits[card.get_suit()], lowest_rank)
                # Since cards is sorted, the first straight flush detected is guaranteed to be the highest one
                if straight:
                    return straight
        return None
