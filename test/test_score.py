import unittest
import time
from poker import HandEvaluator, Card, \
    TraditionalPokerScoreDetector, TraditionalPokerScore, \
    HoldemPokerScore, HoldemPokerScoreDetector


class CardTests(unittest.TestCase):
    def _test_card(self):
        card = Card(3, 2)
        self.assertEquals(3, card.rank)
        self.assertEquals(2, card.suit)


class TraditionalPokerScoreDetectorTests(unittest.TestCase):
    def _test_detect(self, cards, expected_category, expected_cards):
        """Helper method"""
        score = TraditionalPokerScoreDetector(lowest_rank=7).get_score(cards)
        self.assertIsInstance(score, TraditionalPokerScore)
        self.assertEqual(score.category, expected_category, "Wrong category detected")
        self.assertEqual(score.cards, expected_cards, "Incorrect cards order")

    def test_detect_highest_card(self):
        expected_category = TraditionalPokerScore.NO_PAIR
        cards = [Card(9, 0), Card(10, 1), Card(7, 2), Card(14, 0), Card(11, 1)]
        expected_cards = [Card(14, 0), Card(11, 1), Card(10, 1), Card(9, 0), Card(7, 2)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_pair(self):
        expected_category = TraditionalPokerScore.PAIR
        cards = [Card(9, 0), Card(10, 1), Card(10, 2), Card(14, 0), Card(11, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(14, 0), Card(11, 1), Card(9, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_double_pair(self):
        expected_category = TraditionalPokerScore.TWO_PAIR
        cards = [Card(9, 0), Card(10, 1), Card(10, 2), Card(14, 0), Card(9, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(9, 1), Card(9, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_three_of_a_kind(self):
        expected_category = TraditionalPokerScore.TRIPS
        cards = [Card(10, 0), Card(10, 1), Card(14, 0), Card(10, 2), Card(9, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(10, 0), Card(14, 0), Card(9, 1)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight(self):
        expected_category = TraditionalPokerScore.STRAIGHT
        cards = [Card(10, 0), Card(13, 1), Card(11, 2), Card(14, 0), Card(12, 1)]
        expected_cards = [Card(14, 0), Card(13, 1), Card(12, 1), Card(11, 2), Card(10, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight_minimum(self):
        expected_category = TraditionalPokerScore.STRAIGHT
        cards = [Card(7, 0), Card(10, 1), Card(8, 2), Card(14, 0), Card(9, 1)]
        expected_cards = [Card(10, 1), Card(9, 1), Card(8, 2), Card(7, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_full_house(self):
        expected_category = TraditionalPokerScore.FULL_HOUSE
        cards = [Card(7, 0), Card(11, 1), Card(7, 2), Card(11, 0), Card(11, 2)]
        expected_cards = [Card(11, 2), Card(11, 1), Card(11, 0), Card(7, 2), Card(7, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_flush(self):
        expected_category = TraditionalPokerScore.FLUSH
        cards = [Card(9, 3), Card(10, 3), Card(7, 3), Card(14, 3), Card(11, 3)]
        expected_cards = [Card(14, 3), Card(11, 3), Card(10, 3), Card(9, 3), Card(7, 3)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_four_of_a_kind(self):
        expected_category = TraditionalPokerScore.QUADS
        cards = [Card(10, 0), Card(10, 1), Card(10, 2), Card(14, 0), Card(10, 3)]
        expected_cards = [Card(10, 3), Card(10, 2), Card(10, 1), Card(10, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight_flush(self):
        expected_category = TraditionalPokerScore.STRAIGHT_FLUSH
        cards = [Card(10, 2), Card(13, 2), Card(11, 2), Card(14, 2), Card(12, 2)]
        expected_cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_longer_sequence(self):
        expected_category = TraditionalPokerScore.TRIPS
        cards = [Card(7, 0), Card(7, 2), Card(8, 0), Card(7, 3), Card(8, 1), Card(8, 2), Card(14, 0)]
        expected_cards = [Card(8, 2), Card(8, 1), Card(8, 0), Card(14, 0), Card(7, 3)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_shorter_sequence(self):
        expected_category = TraditionalPokerScore.TRIPS
        cards = [Card(8, 0), Card(7, 3), Card(8, 1), Card(8, 2)]
        expected_cards = [Card(8, 2), Card(8, 1), Card(8, 0), Card(7, 3)]
        self._test_detect(cards, expected_category, expected_cards)


class HoldemPokerScoreDetectorTests(unittest.TestCase):
    def _test_detect(self, cards, expected_category, expected_cards):
        """Helper method"""
        score = HoldemPokerScoreDetector().get_score(cards)
        self.assertIsInstance(score, HoldemPokerScore)
        self.assertEqual(score.category, expected_category, "Wrong category detected")
        self.assertEqual(score.cards, expected_cards, "Incorrect cards order")

    def test_detect_highest_card(self):
        expected_category = HoldemPokerScore.NO_PAIR
        cards = [Card(9, 0), Card(10, 1), Card(7, 2), Card(14, 0), Card(11, 1)]
        expected_cards = [Card(14, 0), Card(11, 1), Card(10, 1), Card(9, 0), Card(7, 2)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_pair(self):
        expected_category = HoldemPokerScore.PAIR
        cards = [Card(9, 0), Card(10, 1), Card(14, 0), Card(10, 2), Card(11, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(14, 0), Card(11, 1), Card(9, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_double_pair(self):
        expected_category = HoldemPokerScore.TWO_PAIR
        cards = [Card(9, 0), Card(10, 1), Card(10, 2), Card(14, 0), Card(9, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(9, 1), Card(9, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_three_of_a_kind(self):
        expected_category = HoldemPokerScore.TRIPS
        cards = [Card(10, 0), Card(10, 1), Card(14, 0), Card(10, 2), Card(9, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(10, 0), Card(14, 0), Card(9, 1)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight(self):
        expected_category = HoldemPokerScore.STRAIGHT
        cards = [Card(10, 0), Card(13, 1), Card(11, 2), Card(14, 0), Card(12, 1)]
        expected_cards = [Card(14, 0), Card(13, 1), Card(12, 1), Card(11, 2), Card(10, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight_minimum(self):
        expected_category = HoldemPokerScore.STRAIGHT
        cards = [Card(2, 0), Card(5, 1), Card(3, 2), Card(14, 0), Card(4, 1)]
        expected_cards = [Card(5, 1), Card(4, 1), Card(3, 2), Card(2, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_full_house(self):
        expected_category = HoldemPokerScore.FULL_HOUSE
        cards = [Card(7, 0), Card(11, 1), Card(7, 2), Card(11, 0), Card(11, 2)]
        expected_cards = [Card(11, 2), Card(11, 1), Card(11, 0), Card(7, 2), Card(7, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_flush(self):
        expected_category = HoldemPokerScore.FLUSH
        cards = [Card(9, 3), Card(10, 3), Card(7, 3), Card(14, 3), Card(11, 3)]
        expected_cards = [Card(14, 3), Card(11, 3), Card(10, 3), Card(9, 3), Card(7, 3)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_four_of_a_kind(self):
        expected_category = HoldemPokerScore.QUADS
        cards = [Card(10, 0), Card(10, 1), Card(10, 2), Card(14, 0), Card(10, 3)]
        expected_cards = [Card(10, 3), Card(10, 2), Card(10, 1), Card(10, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight_flush(self):
        expected_category = HoldemPokerScore.STRAIGHT_FLUSH
        cards = [Card(10, 2), Card(13, 2), Card(11, 2), Card(14, 2), Card(12, 2)]
        expected_cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_min_straight_flush(self):
        expected_category = HoldemPokerScore.STRAIGHT_FLUSH
        cards = [Card(14, 2), Card(3, 2), Card(2, 2), Card(5, 2), Card(4, 2)]
        expected_cards = [Card(5, 2), Card(4, 2), Card(3, 2), Card(2, 2), Card(14, 2)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_longer_sequence(self):
        expected_category = HoldemPokerScore.TRIPS
        cards = [Card(7, 0), Card(7, 2), Card(8, 0), Card(7, 3), Card(8, 1), Card(8, 2), Card(14, 0)]
        expected_cards = [Card(8, 2), Card(8, 1), Card(8, 0), Card(14, 0), Card(7, 3)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_shorter_sequence(self):
        expected_category = HoldemPokerScore.TRIPS
        cards = [Card(8, 0), Card(7, 3), Card(8, 1), Card(8, 2)]
        expected_cards = [Card(8, 2), Card(8, 1), Card(8, 0), Card(7, 3)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_full_houses_over_flush(self):
        expected_category = HoldemPokerScore.FULL_HOUSE
        cards = [
            Card(8, 0), Card(8, 1), Card(8, 2), Card(9, 0), Card(9, 1),
            Card(2, 3), Card(3, 3), Card(4, 3), Card(5, 3), Card(7, 3),
        ]
        expected_cards = [
            Card(8, 2), Card(8, 1), Card(8, 0), Card(9, 1), Card(9, 0)
        ]
        self._test_detect(cards, expected_category, expected_cards)

    def test_pair_with_longer_sequence(self):
        expected_category = HoldemPokerScore.PAIR
        cards = [
            Card(9, 0), Card(8, 0),
            Card(2, 2), Card(3, 0), Card(4, 3), Card(13, 3), Card(8, 3)
        ]
        expected_cards = [
            Card(8, 3), Card(8, 0), Card(13, 3), Card(9, 0), Card(4, 3)
        ]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_and_cmp_integration(self):
        board = [Card(14, 3), Card(14, 2), Card(14, 1), Card(14, 0), Card(13, 0)]
        player1 = [Card(12, 3), Card(9, 2)]
        player2 = [Card(11, 3), Card(7, 2)]

        sd = HoldemPokerScoreDetector()
        score1 = sd.get_score(player1 + board)
        score2 = sd.get_score(player2 + board)
        self.assertEquals(0, score1.cmp(score2))
        self.assertEquals(0, score2.cmp(score1))


class TraditionalPokerScoreTests(unittest.TestCase):
    def test_get_cards(self):
        category = TraditionalPokerScore.STRAIGHT_FLUSH
        cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        score = TraditionalPokerScore(category, cards)
        self.assertEqual(score.cards, cards)

    def test_get_category(self):
        category = TraditionalPokerScore.STRAIGHT_FLUSH
        cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        score = TraditionalPokerScore(category, cards)
        self.assertEqual(score.category, category)

    def _test_cmp(self, score1, score2):
        self.assertGreater(score1.cmp(score2), 0)
        self.assertLess(score2.cmp(score1), 0)

    def test_cmp_different_categories(self):
        highest_card = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(13, 0), Card(11, 1), Card(10, 1), Card(9, 0), Card(7, 2)]
        )
        four_oak = TraditionalPokerScore(
            TraditionalPokerScore.QUADS,
            [Card(14, 3), Card(14, 2), Card(14, 1), Card(14, 0), Card(9, 0)]
        )
        self._test_cmp(four_oak, highest_card)

    def test_cmp_same_categories(self):
        four_9 = TraditionalPokerScore(
            TraditionalPokerScore.QUADS,
            [Card(9, 3), Card(9, 2), Card(9, 1), Card(9, 0), Card(14, 2)]
        )
        four_8 = TraditionalPokerScore(
            TraditionalPokerScore.QUADS,
            [Card(8, 3), Card(8, 2), Card(8, 1), Card(8, 0), Card(14, 0)]
        )
        self._test_cmp(four_9, four_8)

    def test_cmp_same_ranks(self):
        # In the traditional poker game, suits matter (hearts, diamonds, clubs and spades)
        score1 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(14, 1), Card(11, 0), Card(10, 1), Card(9, 0), Card(7, 2)]
        )
        score2 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 1), Card(7, 1)]
        )
        self._test_cmp(score1, score2)

    def test_cmp_same_ranks_same_3_suits(self):
        score1 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        score2 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 1), Card(7, 1)]
        )
        self._test_cmp(score1, score2)

    def test_cmp_same_cards(self):
        score1 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        score2 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        self.assertEqual(score1.cmp(score2), 0)
        self.assertEqual(score2.cmp(score1), 0)

    def test_cmp_straight_flush(self):
        min_straight = TraditionalPokerScore(
            TraditionalPokerScore.STRAIGHT_FLUSH,
            [Card(10, 3), Card(9, 3), Card(8, 3), Card(7, 3), Card(14, 3)]
        )
        max_straight = TraditionalPokerScore(
            TraditionalPokerScore.STRAIGHT_FLUSH,
            [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        )
        self.assertGreater(min_straight.cmp(max_straight), 0)
        self.assertLess(max_straight.cmp(min_straight), 0)

    def test_cmp_shorter_and_longer_sequence_same_cards(self):
        score1 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        score2 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2)]
        )
        self._test_cmp(score1, score2)

    def test_cmp_shorter_and_longer_sequence_different_ranks(self):
        # Even if score1 is a shorter sequence, it's still stronger than score2 because of the card ranks
        score1 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(13, 0), Card(11, 1), Card(10, 3), Card(10, 2)]
        )
        score2 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(13, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        self._test_cmp(score1, score2)

    def test_cmp_shorter_and_longer_sequence_same_ranks(self):
        # In this scenario, even if score2 has better cards according the the suits, score1 is still stronger as it has
        # the same ranks but it's a longer sequence.
        # When comparing two scores with a different sequence size, suits are not taken into account.
        score1 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(13, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        score2 = TraditionalPokerScore(
            TraditionalPokerScore.NO_PAIR,
            [Card(13, 3), Card(11, 3), Card(10, 3), Card(9, 2)]
        )
        self._test_cmp(score1, score2)


class HoldemPokerScoreTests(unittest.TestCase):
    def test_get_cards(self):
        category = HoldemPokerScore.STRAIGHT_FLUSH
        cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        score = HoldemPokerScore(category, cards)
        self.assertEqual(score.cards, cards)

    def test_get_category(self):
        category = HoldemPokerScore.STRAIGHT_FLUSH
        cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        score = HoldemPokerScore(category, cards)
        self.assertEqual(score.category, category)

    def _test_cmp(self, score1, score2):
        self.assertGreater(score1.cmp(score2), 0)
        self.assertLess(score2.cmp(score1), 0)

    def test_cmp_different_categories(self):
        highest_card = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(13, 0), Card(11, 1), Card(10, 1), Card(9, 0), Card(7, 2)]
        )
        four_oak = HoldemPokerScore(
            HoldemPokerScore.QUADS,
            [Card(14, 3), Card(14, 2), Card(14, 1), Card(14, 0), Card(9, 0)]
        )
        self._test_cmp(four_oak, highest_card)

    def test_cmp_same_categories(self):
        four_9 = HoldemPokerScore(
            HoldemPokerScore.QUADS,
            [Card(9, 3), Card(9, 2), Card(9, 1), Card(9, 0), Card(14, 2)]
        )
        four_8 = HoldemPokerScore(
            HoldemPokerScore.QUADS,
            [Card(8, 3), Card(8, 2), Card(8, 1), Card(8, 0), Card(14, 0)]
        )
        self._test_cmp(four_9, four_8)

    def test_cmp_same_ranks(self):
        score1 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(14, 1), Card(11, 0), Card(10, 1), Card(9, 0), Card(7, 2)]
        )
        score2 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 1), Card(7, 1)]
        )
        self.assertEqual(score1.cmp(score2), 0)
        self.assertEqual(score2.cmp(score1), 0)

    def test_cmp_same_ranks_same_3_suits(self):
        score1 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        score2 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 1), Card(7, 1)]
        )
        self.assertEqual(score1.cmp(score2), 0)
        self.assertEqual(score2.cmp(score1), 0)

    def test_cmp_same_cards(self):
        score1 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        score2 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        self.assertEqual(score1.cmp(score2), 0)
        self.assertEqual(score2.cmp(score1), 0)

    def test_cmp_straight_flush(self):
        min_straight = HoldemPokerScore(
            HoldemPokerScore.STRAIGHT_FLUSH,
            [Card(5, 3), Card(4, 3), Card(3, 3), Card(2, 3), Card(14, 3)]
        )
        max_straight = HoldemPokerScore(
            HoldemPokerScore.STRAIGHT_FLUSH,
            [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        )
        self.assertLess(min_straight.cmp(max_straight), 0)
        self.assertGreater(max_straight.cmp(min_straight), 0)

    def test_cmp_shorter_and_longer_sequence_same_cards(self):
        score1 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        score2 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2)]
        )
        self._test_cmp(score1, score2)

    def test_cmp_shorter_and_longer_sequence_different_ranks(self):
        # Even if score1 is a shorter sequence, it's still stronger than score2 because of the card ranks
        score1 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(13, 0), Card(11, 1), Card(10, 3), Card(10, 2)]
        )
        score2 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(13, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        self._test_cmp(score1, score2)

    def test_cmp_shorter_and_longer_sequence_same_ranks(self):
        # In this scenario, even if score2 has better cards according the the suits, score1 is still stronger as it has
        # the same ranks but it's a longer sequence.
        # When comparing two scores with a different sequence size, suits are not taken into account.
        score1 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(13, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)]
        )
        score2 = HoldemPokerScore(
            HoldemPokerScore.NO_PAIR,
            [Card(13, 3), Card(11, 3), Card(10, 3), Card(9, 2)]
        )
        self._test_cmp(score1, score2)

    def test_cmp_AA_with_AA(self):
        score1 = HoldemPokerScore(
            HoldemPokerScore.PAIR,
            [Card(14, 3), Card(14, 2)]
        )
        score2 = HoldemPokerScore(
            HoldemPokerScore.PAIR,
            [Card(14, 1), Card(14, 0)]
        )
        self.assertEquals(0, score1.cmp(score2))
        self.assertEquals(0, score2.cmp(score1))


if __name__ == '__main__':
    unittest.main()
