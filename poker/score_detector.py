import ctypes
import collections
from math import factorial
import gevent
import random
import time
from poker import Card
from multiprocessing import Process, Queue, Manager, Value, Lock
from Queue import Empty


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
            return self._merge_with_cards(quads_list[0])[0:5]
        except IndexError:
            return None

    def full_house(self):
        trips_list = self._x_sorted_list(3)
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(trips_list[0] + pair_list[0])[0:5]
        except IndexError:
            return None

    def trips(self):
        trips_list = self._x_sorted_list(3)
        try:
            return self._merge_with_cards(trips_list[0])[0:5]
        except IndexError:
            return None

    def two_pair(self):
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(pair_list[0] + pair_list[1])[0:5]
        except IndexError:
            return None

    def pair(self):
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(pair_list[0])[0:5]
        except IndexError:
            return None

    def straight(self):
        return self._get_straight(self._sorted)

    def flush(self):
        suits = collections.defaultdict(list)
        for card in self._sorted:
            suits[card.suit].append(card)
            # Since cards is sorted, the first flush detected is guaranteed to be the highest one
            if len(suits[card.suit]) == 5:
                return suits[card.suit]
        return None

    def straight_flush(self):
        suits = collections.defaultdict(list)
        for card in self._sorted:
            suits[card.suit].append(card)
            if len(suits[card.suit]) >= 5:
                straight = self._get_straight(suits[card.suit])
                # Since cards is sorted, the first straight flush detected is guaranteed to be the highest one
                if straight:
                    return straight
        return None

    def no_pair(self):
        return self._sorted[0:5]


class Score:
    def __init__(self, category, cards):
        self._category = category
        self._cards = cards
        assert(len(cards) <= 5)

    @property
    def category(self):
        """Gets the category for this score."""
        return self._category

    @property
    def cards(self):
        return self._cards

    @property
    def strength(self):
        raise NotImplemented

    def cmp(self, other):
        return cmp(self.strength, other.strength)

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

    @property
    def strength(self):
        strength = self.category
        for offset in range(5):
            strength <<= 4
            try:
                strength += self.cards[offset].rank
            except IndexError:
                pass
        for offset in range(5):
            strength <<= 2
            try:
                strength += self.cards[offset].suit
            except IndexError:
                pass
        return strength

    def cmp(self, other):
        # Same score, compare the list of cards
        cards1 = self.cards
        cards2 = other.cards

        # In a traditional poker, royal flushes are weaker than minimum straight flushes
        # This is done so you are not mathematically sure to have the strongest hand.
        if self.category == TraditionalPokerScore.STRAIGHT_FLUSH:
            if TraditionalPokerScore._straight_is_max(cards1) and TraditionalPokerScore._straight_is_min(cards2):
                return -1
            elif TraditionalPokerScore._straight_is_min(cards1) and TraditionalPokerScore._straight_is_max(cards2):
                return 1

        return cmp(self.strength, other.strength)

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

    @property
    def strength(self):
        strength = self.category
        for offset in range(5):
            strength <<= 4
            try:
                strength += self.cards[offset].rank
            except IndexError:
                pass
        return strength

    def cmp(self, other):
        return cmp(self.strength, other.strength)


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
            cards = score_function()
            if cards:
                return HoldemPokerScore(score_category, cards)

        raise RuntimeError("Unable to detect the score")


class HandEvaluator:
    MAX_WORKERS = 4
    BOARD_SIZE = 5

    class EvaluationResults:
        def __init__(self):
            self._lock = Lock()
            m = Manager()
            self._wins = m.Value(ctypes.c_char_p, "0")
            self._ties = m.Value(ctypes.c_char_p, "0")
            self._defeats = m.Value(ctypes.c_char_p, "0")

        @property
        def wins(self):
            return long(self._wins.value)

        @property
        def ties(self):
            return long(self._ties.value)

        @property
        def defeats(self):
            return long(self._defeats.value)

        def update(self, wins, ties, defeats):
            with self._lock:
                self._wins.value = str(self.wins + wins)
                self._ties.value = str(self.ties + ties)
                self._defeats.value = str(self.defeats + defeats)

    def __init__(self, score_detector):
        self.score_detector = score_detector

    def hand_strength(self, my_cards, board, num_followers, look_ahead=None, timeout=None):
        wins, ties, defeats = self.evaluate(my_cards, board, num_followers, look_ahead=look_ahead, timeout=timeout)
        return float(wins + ties) / float(wins + ties + defeats)

    def evaluate(self, my_cards, board, num_followers, look_ahead=None, timeout=None):
        deck = filter(
            lambda card: card not in my_cards and card not in board,
            [Card(rank, suit) for rank in range(2, 15) for suit in range(0, 4)]
        )
        random.shuffle(deck)

        if look_ahead is None:
            look_ahead = HandEvaluator.BOARD_SIZE - len(board)
        assert(look_ahead <= HandEvaluator.BOARD_SIZE)

        timeout_epoch = None if timeout is None else time.time() + timeout

        request_queue = Queue(10)
        in_progress = Value("b", True)

        results = HandEvaluator.EvaluationResults()

        # Generating queue items
        requests_process = Process(
            target=self._evaluate_boards,
            args=(request_queue, deck, look_ahead, timeout_epoch, in_progress)
        )
        requests_process.start()

        workers = []
        for i in range(HandEvaluator.MAX_WORKERS):
            worker = Process(
                target=self._evaluate_worker,
                args=(my_cards, board, deck, num_followers, request_queue, in_progress, results)
            )
            worker.start()
            workers.append(worker)

        # Waiting for every process to finish
        requests_process.join()
        for worker in workers:
            worker.join()

        return results.wins, results.ties, results.defeats

    def _evaluate_boards(self, request_queue, deck, size, timeout_epoch, in_progress):
        class Timeout(Exception):
            pass

        def generate(future_board, iteration):
            if timeout_epoch is not None and time.time() > timeout_epoch:
                raise Timeout
            if len(future_board) == size:
                request_queue.put(future_board)
            else:
                for key in range(iteration, len(deck)):
                    generate(future_board + [deck[key]], key + 1)

        try:
            generate([], 0)
        except Timeout:
            pass
        finally:
            in_progress.value = False

    def _evaluate_worker(self, my_cards, board, deck, num_followers, requests_queue, in_progress, results):
        while True:
            try:
                future_board = requests_queue.get_nowait()
                wins, ties, defeats = self.evaluate_base(
                    my_cards,
                    board + future_board,
                    filter(lambda card: card not in future_board, deck),
                    num_followers
                )
                results.update(wins, ties, defeats)
            except Empty:
                if not in_progress.value:
                    break
                gevent.sleep(0.1)

    def evaluate_base(self, my_cards, board, deck, num_followers):
        def combinations(source, size):
            def combine(target, iteration):
                result = []
                if len(target) == size:
                    result.append(target)
                else:
                    for key in range(iteration, len(source)):
                        result += combine(target + [source[key]], key + 1)
                return result

            return combine([], 0)

        my_score = self.score_detector.get_score(my_cards + board)

        wins = 0
        ties = 0
        defeats = 0

        for opponent_cards in combinations(deck, len(my_cards)):
            opponent_score = self.score_detector.get_score(opponent_cards + board)
            score_diff = my_score.cmp(opponent_score)
            if score_diff < 0:
                defeats += 1
            elif score_diff == 0:
                ties += 1
            else:
                wins += 1

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # followers
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Let's assume this situation:
        # followers: 4
        # wins: 5
        # ties: 6
        # defeats: 5

        # To win, I need to defeat every other player otherwise I either loose or tie
        # C(5, 4) = 5
        # To tie, I need to have exactly the same score of at least one other player, and defeating every other
        # C(6 + 5, 4) - wins = 10
        # With any other combination I loose
        # C(5 + 6 + 5, 4) - wins - ties

        # To win a hand, I need to win against every other player
        # If I win against 6 possible hands and there are 4 players
        # this means there are C(10, 4) possible combinations for me to win against everyone

        if wins < num_followers:
            win_combs = 0
        else:
            win_combs = factorial(wins) / factorial(num_followers) / factorial(wins - num_followers)

        # @todo: this seems wrong. it seems we'd need to subtract defeats combinations from here double check this logic
        if ties + wins < num_followers:
            tie_combs = 0
        else:
            tie_combs = factorial(ties + wins) / factorial(num_followers) / factorial(ties + wins - num_followers)

        tie_combs -= win_combs

        all_cases = wins + ties + defeats
        all_combinations = factorial(all_cases) / factorial(num_followers) / factorial(all_cases - num_followers)
        defeat_combs = all_combinations - win_combs - tie_combs

        return win_combs, tie_combs, defeat_combs

    # def evaluate_base(self, my_cards, board, deck):
    #     my_score = self.score_detector.get_score(my_cards + board)
    #
    #     def evaluate(opponent_cards, start_key):
    #         wins = 0
    #         ties = 0
    #         defeats = 0
    #
    #         if len(opponent_cards) == len(my_cards):
    #             opponent_score = self.score_detector.get_score(opponent_cards + board)
    #             score_diff = my_score.cmp(opponent_score)
    #             if score_diff < 0:
    #                 defeats = 1
    #             elif score_diff == 0:
    #                 ties = 1
    #             else:
    #                 wins = 1
    #
    #         else:
    #             for key in range(start_key, len(deck)):
    #                 sub_wins, sub_ties, sub_defeats = evaluate(
    #                     opponent_cards=opponent_cards + [deck[key]],
    #                     start_key=key + 1
    #                 )
    #                 wins += sub_wins
    #                 ties += sub_ties
    #                 defeats += sub_defeats
    #
    #         return wins, ties, defeats
    #     return evaluate([], 0)
