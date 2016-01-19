import unittest
from poker import ScoreDetector, Score, Card


class ScoreDetectorTests(unittest.TestCase):
    def _test_detect(self, cards, expected_category, expected_cards):
        """Helper method"""
        actual_category, actual_cards = ScoreDetector(lowest_rank=7).detect_score(cards)
        self.assertEqual(actual_category, expected_category, "Wrong category detected")
        self.assertEqual(actual_cards, expected_cards, "Incorrect cards order")

    def test_detect_highest_card(self):
        expected_category = Score.HIGHEST_CARD
        cards = [Card(9, 0), Card(10, 1), Card(7, 2), Card(14, 0), Card(11, 1)]
        expected_cards = [Card(14, 0), Card(11, 1), Card(10, 1), Card(9, 0), Card(7, 2)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_pair(self):
        expected_category = Score.PAIR
        cards = [Card(9, 0), Card(10, 1), Card(10, 2), Card(14, 0), Card(11, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(14, 0), Card(11, 1), Card(9, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_double_pair(self):
        expected_category = Score.DOUBLE_PAIR
        cards = [Card(9, 0), Card(10, 1), Card(10, 2), Card(14, 0), Card(9, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(9, 1), Card(9, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_three_of_a_kind(self):
        expected_category = Score.THREE_OF_A_KIND
        cards = [Card(10, 0), Card(10, 1), Card(14, 0), Card(10, 2), Card(9, 1)]
        expected_cards = [Card(10, 2), Card(10, 1), Card(10, 0), Card(14, 0), Card(9, 1)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight(self):
        expected_category = Score.STRAIGHT
        cards = [Card(10, 0), Card(13, 1), Card(11, 2), Card(14, 0), Card(12, 1)]
        expected_cards = [Card(14, 0), Card(13, 1), Card(12, 1), Card(11, 2), Card(10, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight_minimum(self):
        expected_category = Score.STRAIGHT
        cards = [Card(7, 0), Card(10, 1), Card(8, 2), Card(14, 0), Card(9, 1)]
        expected_cards = [Card(10, 1), Card(9, 1), Card(8, 2), Card(7, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_full_house(self):
        expected_category = Score.FULL_HOUSE
        cards = [Card(7, 0), Card(11, 1), Card(7, 2), Card(11, 0), Card(11, 2)]
        expected_cards = [Card(11, 2), Card(11, 1), Card(11, 0), Card(7, 2), Card(7, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_flush(self):
        expected_category = Score.FLUSH
        cards = [Card(9, 3), Card(10, 3), Card(7, 3), Card(14, 3), Card(11, 3)]
        expected_cards = [Card(14, 3), Card(11, 3), Card(10, 3), Card(9, 3), Card(7, 3)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_four_of_a_kind(self):
        expected_category = Score.FOUR_OF_A_KIND
        cards = [Card(10, 0), Card(10, 1), Card(10, 2), Card(14, 0), Card(10, 3)]
        expected_cards = [Card(10, 3), Card(10, 2), Card(10, 1), Card(10, 0), Card(14, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_straight_flush(self):
        expected_category = Score.STRAIGHT_FLUSH
        cards = [Card(10, 2), Card(13, 2), Card(11, 2), Card(14, 2), Card(12, 2)]
        expected_cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_longer_sequence(self):
        expected_category = Score.THREE_OF_A_KIND
        cards = [Card(7, 0), Card(7, 2), Card(8, 0), Card(7, 3), Card(8, 1), Card(8, 2), Card(14, 0)]
        expected_cards = [Card(8, 2), Card(8, 1), Card(8, 0), Card(14, 0), Card(7, 3), Card(7, 2), Card(7, 0)]
        self._test_detect(cards, expected_category, expected_cards)

    def test_detect_shorter_sequence(self):
        expected_category = Score.THREE_OF_A_KIND
        cards = [Card(8, 0), Card(7, 3), Card(8, 1), Card(8, 2)]
        expected_cards = [Card(8, 2), Card(8, 1), Card(8, 0), Card(7, 3)]
        self._test_detect(cards, expected_category, expected_cards)


class ScoreTests(unittest.TestCase):
    def test_get_cards(self):
        category = Score.STRAIGHT_FLUSH
        cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        score = Score(category, cards)
        self.assertEqual(score.get_cards(), cards)

    def test_get_category(self):
        category = Score.STRAIGHT_FLUSH
        cards = [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)]
        score = Score(category, cards)
        self.assertEqual(score.get_category(), category)

    def _test_cmp(self, score1, score2):
        self.assertGreater(score1.cmp(score2), 0)
        self.assertLess(score2.cmp(score1), 0)

    def test_cmp_different_categories(self):
        highest_card = Score(Score.HIGHEST_CARD, [Card(13, 0), Card(11, 1), Card(10, 1), Card(9, 0), Card(7, 2)])
        four_oak = Score(Score.FOUR_OF_A_KIND, [Card(14, 3), Card(14, 2), Card(14, 1), Card(14, 0), Card(9, 0)])
        self._test_cmp(four_oak, highest_card)

    def test_cmp_same_categories(self):
        four_9 = Score(Score.FOUR_OF_A_KIND, [Card(9, 3), Card(9, 2), Card(9, 1), Card(9, 0), Card(14, 2)])
        four_8 = Score(Score.FOUR_OF_A_KIND, [Card(8, 3), Card(8, 2), Card(8, 1), Card(8, 0), Card(14, 0)])
        self._test_cmp(four_9, four_8)

    def test_cmp_same_ranks(self):
        score1 = Score(Score.HIGHEST_CARD, [Card(14, 1), Card(11, 0), Card(10, 1), Card(9, 0), Card(7, 2)])
        score2 = Score(Score.HIGHEST_CARD, [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 1), Card(7, 1)])
        self._test_cmp(score1, score2)

    def test_cmp_same_ranks_same_3_suits(self):
        score1 = Score(Score.HIGHEST_CARD, [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)])
        score2 = Score(Score.HIGHEST_CARD, [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 1), Card(7, 1)])
        self._test_cmp(score1, score2)

    def test_cmp_same_cards(self):
        score1 = Score(Score.HIGHEST_CARD, [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)])
        score2 = Score(Score.HIGHEST_CARD, [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)])
        self.assertEqual(score1.cmp(score2), 0)
        self.assertEqual(score2.cmp(score1), 0)

    def test_cmp_straight_flush(self):
        min_straight = Score(Score.STRAIGHT_FLUSH, [Card(10, 3), Card(9, 3), Card(8, 3), Card(7, 3), Card(14, 3)])
        max_straight = Score(Score.STRAIGHT_FLUSH, [Card(14, 2), Card(13, 2), Card(12, 2), Card(11, 2), Card(10, 2)])
        self.assertGreater(min_straight.cmp(max_straight), 0)
        self.assertLess(max_straight.cmp(min_straight), 0)

    def test_cmp_shorter_and_longer_sequence_same_cards(self):
        score1 = Score(Score.HIGHEST_CARD, [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)])
        score2 = Score(Score.HIGHEST_CARD, [Card(14, 0), Card(11, 1), Card(10, 3), Card(9, 2)])
        self._test_cmp(score1, score2)

    def test_cmp_shorter_and_longer_sequence_different_ranks(self):
        # Even if score1 is a shorter sequence, it's still stronger than score2 because of the card ranks
        score1 = Score(Score.HIGHEST_CARD, [Card(13, 0), Card(11, 1), Card(10, 3), Card(10, 2)])
        score2 = Score(Score.HIGHEST_CARD, [Card(13, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)])
        self._test_cmp(score1, score2)

    def test_cmp_shorter_and_longer_sequence_same_ranks(self):
        # In this scenario, even if score2 has better cards according the the suits, score1 is still stronger as it has
        # the same ranks but it's a longer sequence.
        # When comparing two scores with a different sequence size, suits are not taken into account.
        score1 = Score(Score.HIGHEST_CARD, [Card(13, 0), Card(11, 1), Card(10, 3), Card(9, 2), Card(7, 2)])
        score2 = Score(Score.HIGHEST_CARD, [Card(13, 3), Card(11, 3), Card(10, 3), Card(9, 2)])
        self._test_cmp(score1, score2)


if __name__ == '__main__':
    unittest.main()

