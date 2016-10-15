import unittest
from poker import Player
from poker.solid_game import *


class GamePlayersTest(unittest.TestCase):
    def _create_game_players(self):
        return GamePlayers([
            Player("player-1", "Player One", 1000.0),
            Player("player-2", "Player Two", 1000.0),
            Player("player-3", "Player Three", 0.0),
            Player("player-4", "Player Four", 1000.0),
        ])

    def test_round(self):
        game_players = self._create_game_players()
        round = game_players.round("player-2")
        self.assertEqual("player-2", round.next().id)
        self.assertEqual("player-3", round.next().id)
        self.assertEqual("player-4", round.next().id)
        self.assertEqual("player-1", round.next().id)
        self.assertRaises(StopIteration, round.next)

    def test_round_with_fold(self):
        game_players = self._create_game_players()
        game_players.fold("player-4")
        round = game_players.round("player-2")
        self.assertEqual("player-2", round.next().id)
        self.assertEqual("player-3", round.next().id)
        self.assertEqual("player-1", round.next().id)
        self.assertRaises(StopIteration, round.next)

    def test_round_with_no_dealer(self):
        game_players = self._create_game_players()
        game_players.fold("player-2")
        round = game_players.round("player-2")
        self.assertEqual("player-3", round.next().id)
        self.assertEqual("player-4", round.next().id)
        self.assertEqual("player-1", round.next().id)
        self.assertRaises(StopIteration, round.next)

    def test_round_with_no_players(self):
        game_players = self._create_game_players()
        game_players.fold("player-1")
        game_players.fold("player-2")
        game_players.fold("player-3")
        game_players.fold("player-4")
        round = game_players.round("player-2")
        self.assertRaises(StopIteration, round.next)

    def test_get_next(self):
        game_players = self._create_game_players()
        self.assertEqual("player-3", game_players.get_next("player-2").id)

    def test_get_next_with_no_next(self):
        game_players = self._create_game_players()
        game_players.fold("player-3")
        self.assertEqual("player-4", game_players.get_next("player-2").id)

    def test_get_next_with_no_dealer_raises_exception(self):
        game_players = self._create_game_players()
        game_players.fold("player-2")
        self.assertRaises(ValueError, game_players.get_next, "player-2")

    def test_get_next_with_only_dealer_throws_exception(self):
        game_players = self._create_game_players()
        game_players.fold("player-1")
        game_players.fold("player-3")
        game_players.fold("player-4")
        self.assertIsNone(game_players.get_next("player-2"))

    def test_get_previous(self):
        game_players = self._create_game_players()
        self.assertEqual("player-1", game_players.get_previous("player-2").id)

    def test_get_previous_with_no_previous(self):
        game_players = self._create_game_players()
        game_players.fold("player-1")
        self.assertEqual("player-4", game_players.get_previous("player-2").id)

    def test_get_previous_with_no_dealer_raises_exception(self):
        game_players = self._create_game_players()
        game_players.fold("player-2")
        self.assertRaises(ValueError, game_players.get_previous, "player-2")

    def test_get_previous_with_only_dealer_throws_exception(self):
        game_players = self._create_game_players()
        game_players.fold("player-1")
        game_players.fold("player-3")
        game_players.fold("player-4")
        self.assertIsNone(game_players.get_previous("player-2"))

    def test_is_active_with_fold(self):
        game_players = self._create_game_players()
        self.assertTrue(game_players.is_active("player-2"))
        game_players.fold("player-2")
        self.assertFalse(game_players.is_active("player-2"))

    def test_is_active_with_remove(self):
        game_players = self._create_game_players()
        self.assertTrue(game_players.is_active("player-2"))
        game_players.remove("player-2")
        self.assertFalse(game_players.is_active("player-2"))

    def test_count_active(self):
        game_players = self._create_game_players()
        self.assertEquals(4, game_players.count_active())
        game_players.fold("player-2")
        self.assertEquals(3, game_players.count_active())

    def test_count_active_with_money(self):
        game_players = self._create_game_players()
        self.assertEqual(3, game_players.count_active_with_money())
        game_players.fold("player-2")
        self.assertEquals(2, game_players.count_active_with_money())
        game_players.fold("player-3")
        self.assertEquals(2, game_players.count_active_with_money())

    def test_reset(self):
        game_players = self._create_game_players()
        game_players.fold("player-2")
        self.assertFalse(game_players.is_active("player-2"))
        game_players.reset()
        self.assertTrue(game_players.is_active("player-2"))

    def test_reset_with_remove(self):
        game_players = self._create_game_players()
        game_players.remove("player-2")
        self.assertFalse(game_players.is_active("player-2"))
        game_players.reset()
        self.assertFalse(game_players.is_active("player-2"))


class GamePotsTest(unittest.TestCase):
    def test_add_bets_with_one_round(self):
        player1 = Player("player-1", "Player One", 1000)
        player2 = Player("player-2", "Player Two", 1000)
        player3 = Player("player-3", "Player Three", 1000)
        player4 = Player("player-4", "Player Four", 1000)

        game_players = GamePlayers([player1, player2, player3, player4])
        game_pots = GamePots(game_players)

        game_pots.add_bets({"player-1": 500, "player-2": 0.0, "player-3": 800, "player-4": 800})

        pots = game_pots.pots

        self.assertEqual(2, len(pots))

        self.assertEquals(1500, pots[0].money)
        self.assertEquals([player1, player3, player4], pots[0].players)

        self.assertEquals(600, pots[1].money)
        self.assertEquals([player3, player4], pots[1].players)

    def test_add_bets_with_two_rounds(self):
        player1 = Player("player-1", "Player One", 1000)
        player2 = Player("player-2", "Player Two", 1000)
        player3 = Player("player-3", "Player Three", 1000)
        player4 = Player("player-4", "Player Four", 1000)

        game_players = GamePlayers([player1, player2, player3, player4])
        game_pots = GamePots(game_players)

        game_pots.add_bets({"player-1": 100, "player-2": 200.0, "player-3": 200, "player-4": 200})
        game_pots.add_bets({"player-1": 0, "player-2": 50.0, "player-3": 100, "player-4": 100})

        pots = game_pots.pots

        self.assertEqual(3, len(pots))

        self.assertEquals(400, pots[0].money)
        self.assertEquals([player1, player2, player3, player4], pots[0].players)

        self.assertEquals(450, pots[1].money)
        self.assertEquals([player2, player3, player4], pots[1].players)

        self.assertEquals(100, pots[2].money)
        self.assertEquals([player2, player3, player4], pots[1].players)


class GameScoresTest(unittest.TestCase):
    class ScoreDetectorMock:
        def get_score(self, cards):
            return "score({})".format(",".join(cards))

    def test_get_shared_cards(self):
        scores = GameScores(self.ScoreDetectorMock())
        self.assertListEqual([], scores.shared_cards)

    def test_add_shared_cards(self):
        scores = GameScores(self.ScoreDetectorMock())
        scores.add_shared_cards(["1", "2", "3"])
        self.assertListEqual(["1", "2", "3"], scores.shared_cards)

    def test_add_shared_cards_multiple(self):
        scores = GameScores(self.ScoreDetectorMock())
        scores.add_shared_cards(["1", "2", "3"])
        scores.add_shared_cards(["4"])
        scores.add_shared_cards(["5"])
        self.assertListEqual(["1", "2", "3", "4", "5"], scores.shared_cards)

    def test_get_cards_with_no_cards_set(self):
        scores = GameScores(self.ScoreDetectorMock())
        self.assertRaises(KeyError, scores.player_cards, "player-123")

    def test_get_score_with_no_cards_set(self):
        scores = GameScores(self.ScoreDetectorMock())
        self.assertRaises(KeyError, scores.player_score, "player-123")

    def test_assign_and_get_cards(self):
        cards = ["1", "2", "3", "4", "5"]
        scores = GameScores(self.ScoreDetectorMock())
        scores.assign_cards("player-1", cards)
        self.assertListEqual(cards, scores.player_cards("player-1"))

    def test_assign_and_get_score(self):
        cards = ["1", "2", "3", "4", "5"]
        scores = GameScores(self.ScoreDetectorMock())
        scores.assign_cards("player-1", cards)
        self.assertEquals("score(1,2,3,4,5)", scores.player_score("player-1"))

    def test_assign_and_get_score_with_shared_cards(self):
        cards = ["1", "2"]
        shared_cards = ["3", "4", "5"]
        scores = GameScores(self.ScoreDetectorMock())
        scores.add_shared_cards(shared_cards)
        scores.assign_cards("player-1", cards)
        self.assertEquals("score(1,2,3,4,5)", scores.player_score("player-1"))


class GameWinnersDetectorTest(unittest.TestCase):
    def test_get_winners(self):
        player1 = Player("player-1", "Player One", 1000.0)
        player2 = Player("player-2", "Player Two", 1000.0)
        player3 = Player("player-3", "Player Three", 1000.0)
        player4 = Player("player-4", "Player Four", 1000.0)

        players = GamePlayers([player1, player2, player3, player4])

        class ScoreMock:
            def __init__(self, value):
                self.value = value

            def cmp(self, other):
                return cmp(self.value, other.value)

        class GameScoresMock:
            def player_score(self, player_id):
                if player_id == "player-1":
                    return ScoreMock(3)
                elif player_id == "player-2":
                    return ScoreMock(2)
                elif player_id == "player-3":
                    return ScoreMock(2)
                elif player_id == "player-4":
                    return ScoreMock(1)
                else:
                    raise ValueError("Unknown player id")

        winner_detector = GameWinnersDetector(players)

        winners = winner_detector.get_winners([player2, player3, player4], GameScoresMock())
        self.assertListEqual([player2, player3], winners)

        winners = winner_detector.get_winners([player1, player2, player3, player4], GameScoresMock())
        self.assertListEqual([player1], winners)

        players.fold("player-1")
        winners = winner_detector.get_winners([player1, player2, player3, player4], GameScoresMock())
        self.assertListEqual([player2, player3], winners)

        players.fold("player-2")
        winners = winner_detector.get_winners([player1, player2, player3, player4], GameScoresMock())
        self.assertListEqual([player3], winners)

        players.fold("player-3")
        winners = winner_detector.get_winners([player1, player2, player3, player4], GameScoresMock())
        self.assertListEqual([player4], winners)

        players.fold("player-4")
        winners = winner_detector.get_winners([player1, player2, player3, player4], GameScoresMock())
        self.assertListEqual([], winners)


class GameBetRounderTest(unittest.TestCase):
    def test_bet_round_everyone_fold(self):
        player1 = Player("player-1", "Player One", 1000.0)
        player2 = Player("player-2", "Player Two", 1000.0)
        player3 = Player("player-3", "Player Three", 1000.0)
        player4 = Player("player-4", "Player Four", 1000.0)

        game_players = GamePlayers([player1, player2, player3, player4])

        def bet_function_mock(player, min_bet, max_bet, bets):
            return -1

        bet_rounder = GameBetRounder(game_players)

        best_player = bet_rounder.bet_round("player-3", {}, bet_function_mock)

        self.assertEquals("player-2", best_player.id)

        self.assertTrue(game_players.is_active("player-2"))
        self.assertFalse(game_players.is_active("player-1"))
        self.assertFalse(game_players.is_active("player-3"))
        self.assertFalse(game_players.is_active("player-4"))

    def test_bet_round_everyone_fold_with_blinds(self):
        bets = {
            "player-1": 400,
            "player-2": 1000
        }

        player1 = Player("player-1", "Player One", 1000.0)
        player2 = Player("player-2", "Player Two", 1000.0)
        player3 = Player("player-3", "Player Three", 1000.0)
        player4 = Player("player-4", "Player Four", 1000.0)

        game_players = GamePlayers([player1, player2, player3, player4])

        def bet_function_mock(player, min_bet, max_bet, bets):
            return -1

        bet_rounder = GameBetRounder(game_players)

        best_player = bet_rounder.bet_round("player-3", bets, bet_function_mock)

        self.assertEquals("player-2", best_player.id)

        self.assertTrue(game_players.is_active("player-2"))
        self.assertFalse(game_players.is_active("player-1"))
        self.assertFalse(game_players.is_active("player-3"))
        self.assertFalse(game_players.is_active("player-4"))

    def test_bet_round_everyone_check(self):
        player1 = Player("player-1", "Player One", 1000.0)
        player2 = Player("player-2", "Player Two", 1000.0)
        player3 = Player("player-3", "Player Three", 1000.0)
        player4 = Player("player-4", "Player Four", 1000.0)

        game_players = GamePlayers([player1, player2, player3, player4])

        def bet_function_mock(player, min_bet, max_bet, bets):
            return min_bet

        bet_rounder = GameBetRounder(game_players)

        best_player = bet_rounder.bet_round("player-3", {}, bet_function_mock)

        self.assertEquals("player-3", best_player.id)

        self.assertTrue(game_players.is_active("player-1"))
        self.assertTrue(game_players.is_active("player-2"))
        self.assertTrue(game_players.is_active("player-3"))
        self.assertTrue(game_players.is_active("player-4"))

    def test_bet_round_everyone_call(self):
        player1 = Player("player-1", "Player One", 1000.0)
        player2 = Player("player-2", "Player Two", 1000.0)
        player3 = Player("player-3", "Player Three", 1000.0)
        player4 = Player("player-4", "Player Four", 1000.0)

        game_players = GamePlayers([player1, player2, player3, player4])

        def bet_function_mock(player, min_bet, max_bet, bets):
            return min_bet

        bet_rounder = GameBetRounder(game_players)

        best_player = bet_rounder.bet_round("player-3", {"player-1": 300, "player-2": 600}, bet_function_mock)

        self.assertEquals("player-3", best_player.id)

        self.assertTrue(game_players.is_active("player-1"))
        self.assertTrue(game_players.is_active("player-2"))
        self.assertTrue(game_players.is_active("player-3"))
        self.assertTrue(game_players.is_active("player-4"))

    # Scenario:
    # - player-2: check
    # - player-3: fold
    # - player-4: raise (all in) - 500
    # - player-1: call - 500
    # - player-2: re-raise - 600
    # - player-1: call - 100 (all-in)
    def test_bet_round_1(self):
        player1 = Player("player-1", "Player One", 600.0)
        player2 = Player("player-2", "Player Two", 1000.0)
        player3 = Player("player-3", "Player Three", 2000.0)
        player4 = Player("player-4", "Player Four", 500.0)

        game_players = GamePlayers([player1, player2, player3, player4])

        bet_rounder = GameBetRounder(game_players)

        bet_calls = {  # Workaround as Python 2.7 doesn't have nonlocal
            "counter": 0
        }

        def bet_function_mock(player, min_bet, max_bet, bets):
            bet_calls["counter"] += 1
            if bet_calls["counter"] == 1:
                self.assertEquals("player-2", player.id)
                self.assertEquals((0.0, 1000.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 0.0, "player-4": 0.0}, bets)
                return 0.0
            elif bet_calls["counter"] == 2:
                self.assertEquals("player-3", player.id)
                self.assertEquals((0.0, 1000.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 0.0, "player-4": 0.0}, bets)
                return -1
            elif bet_calls["counter"] == 3:
                self.assertEquals("player-4", player.id)
                self.assertEquals((0.0, 500.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 0.0, "player-4": 0.0}, bets)
                return 500.0
            elif bet_calls["counter"] == 4:
                self.assertEquals("player-1", player.id)
                self.assertEquals((500.0, 600.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 0.0, "player-4": 500.0}, bets)
                return 500.0
            elif bet_calls["counter"] == 5:
                self.assertEquals("player-2", player.id)
                self.assertEquals((500.0, 600.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 500.0, "player-2": 0.0, "player-3": 0.0, "player-4": 500.0}, bets)
                return 600.0
            elif bet_calls["counter"] == 6:
                self.assertEquals("player-1", player.id)
                self.assertEquals((100.0, 100.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 500.0, "player-2": 600.0, "player-3": 0.0, "player-4": 500.0}, bets)
                return 100.0

        bets = {}
        best_player = bet_rounder.bet_round("player-2", bets, bet_function_mock)

        self.assertEquals(6, bet_calls["counter"])

        # player-1 went all-in
        self.assertTrue(game_players.is_active("player-1"))
        self.assertEqual(0.0, player1.money)

        # player-2 called 600
        self.assertTrue(game_players.is_active("player-2"))
        self.assertEqual(400.0, player2.money)

        # player-3 folded straight away
        self.assertFalse(game_players.is_active("player-3"))
        self.assertEqual(2000.0, player3.money)

        # player-4 went all-in
        self.assertTrue(game_players.is_active("player-4"))
        self.assertEqual(0.0, player4.money)

        # Last raise was by player-2
        self.assertEquals("player-2", best_player.id)
        # Bets dictionary up-to-date
        self.assertEquals({"player-1": 600.0, "player-2": 600.0, "player-3": 0.0, "player-4": 500.0}, bets)

    # Scenario:
    # - player-2: fold
    # - player-3: raise - 200
    # - player-4: re-raise - 600
    # - player-1: all-in - 500
    # - player-3: re-raise - 800
    # - player-4: fold
    def test_bet_round_2(self):
        player1 = Player("player-1", "Player One", 500.0)
        player2 = Player("player-2", "Player Two", 1000.0)
        player3 = Player("player-3", "Player Three", 1000.0)
        player4 = Player("player-4", "Player Four", 2000.0)

        game_players = GamePlayers([player1, player2, player3, player4])

        bet_rounder = GameBetRounder(game_players)

        bet_calls = {  # Workaround as Python 2.7 doesn't have nonlocal
            "counter": 0
        }

        def bet_function_mock(player, min_bet, max_bet, bets):
            bet_calls["counter"] += 1
            if bet_calls["counter"] == 1:
                self.assertEquals("player-2", player.id)
                self.assertEquals((0.0, 1000.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 0.0, "player-4": 0.0}, bets)
                return -1
            if bet_calls["counter"] == 2:
                self.assertEquals("player-3", player.id)
                self.assertEquals((0.0, 1000.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 0.0, "player-4": 0.0}, bets)
                return 200.0
            if bet_calls["counter"] == 3:
                self.assertEquals("player-4", player.id)
                self.assertEquals((200.0, 1000.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 200.0, "player-4": 0.0}, bets)
                return 600.0
            if bet_calls["counter"] == 4:
                self.assertEquals("player-1", player.id)
                self.assertEquals((500.0, 500.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 200.0, "player-4": 600.0}, bets)
                return 500.0
            if bet_calls["counter"] == 5:
                self.assertEquals("player-3", player.id)
                self.assertEquals((400.0, 800.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 500.0, "player-2": 0.0, "player-3": 200.0, "player-4": 600.0}, bets)
                return 800.0
            if bet_calls["counter"] == 6:
                self.assertEquals("player-4", player.id)
                self.assertEquals((400.0, 400.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 500.0, "player-2": 0.0, "player-3": 1000.0, "player-4": 600.0}, bets)
                return -1

        bets = {}

        best_player = bet_rounder.bet_round("player-2", bets, bet_function_mock)

        self.assertEquals(6, bet_calls["counter"])

        # player-1 went all-in
        self.assertTrue(game_players.is_active("player-1"))
        self.assertEqual(0.0, player1.money)

        # player-2 called 600
        self.assertFalse(game_players.is_active("player-2"))
        self.assertEqual(1000.0, player2.money)

        # player-3 folded straight away
        self.assertTrue(game_players.is_active("player-3"))
        self.assertEqual(0.0, player3.money)

        # player-4 went all-in
        self.assertFalse(game_players.is_active("player-4"))
        self.assertEqual(1400.0, player4.money)

        # Last re-raise
        self.assertEquals("player-3", best_player.id)
        self.assertEquals({"player-1": 500.0, "player-2": 0.0, "player-3": 1000.0, "player-4": 600.0}, bets)

    # Scenario:
    # - player-3 small blind, player-4 big blind
    # - player-1: fold
    # - player-2: call - 200
    # - player-3: call - 100
    # - player-4: raise - 200
    # - player-2: fold
    # - player-3: raise - 400
    # - player-4: re-raise - 400
    # - player-3: re-re-raise (all-in) - 400
    # - player-4: call (all-in) - 200
    def test_bet_round_small_and_big_blind(self):
        player1 = Player("player-1", "Player One", 1000.0)
        player2 = Player("player-2", "Player Two", 1000.0)
        player3 = Player("player-3", "Player Three", 900.0)
        player4 = Player("player-4", "Player Four", 800.0)

        game_players = GamePlayers([player1, player2, player3, player4])

        bet_rounder = GameBetRounder(game_players)

        bet_calls = {  # Workaround as Python 2.7 doesn't have nonlocal
            "counter": 0
        }

        def bet_function_mock(player, min_bet, max_bet, bets):
            bet_calls["counter"] += 1
            if bet_calls["counter"] == 1:
                self.assertEquals("player-1", player.id)
                self.assertEquals((200.0, 1000.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 100.0, "player-4": 200.0}, bets)
                return -1
            if bet_calls["counter"] == 2:
                self.assertEquals("player-2", player.id)
                self.assertEquals((200.0, 1000.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 0.0, "player-3": 100.0, "player-4": 200.0}, bets)
                return 200.0
            if bet_calls["counter"] == 3:
                self.assertEquals("player-3", player.id)
                self.assertEquals((100.0, 900.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 200.0, "player-3": 100.0, "player-4": 200.0}, bets)
                return 100.0
            if bet_calls["counter"] == 4:
                self.assertEquals("player-4", player.id)
                self.assertEquals((0.0, 800.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 200.0, "player-3": 200.0, "player-4": 200.0}, bets)
                return 200.0
            if bet_calls["counter"] == 5:
                self.assertEquals("player-2", player.id)
                self.assertEquals((200.0, 800.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 200.0, "player-3": 200.0, "player-4": 400.0}, bets)
                return -1
            if bet_calls["counter"] == 6:
                self.assertEquals("player-3", player.id)
                self.assertEquals((200.0, 800.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 200.0, "player-3": 200.0, "player-4": 400.0}, bets)
                return 400.0
            if bet_calls["counter"] == 7:
                self.assertEquals("player-4", player.id)
                self.assertEquals((200.0, 600.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 200.0, "player-3": 600.0, "player-4": 400.0}, bets)
                return 400.0
            if bet_calls["counter"] == 8:
                self.assertEquals("player-3", player.id)
                self.assertEquals((200.0, 400.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 200.0, "player-3": 600.0, "player-4": 800.0}, bets)
                return 400.0
            if bet_calls["counter"] == 9:
                self.assertEquals("player-4", player.id)
                self.assertEquals((200.0, 200.0), (min_bet, max_bet))
                self.assertEquals({"player-1": 0.0, "player-2": 200.0, "player-3": 1000.0, "player-4": 800.0}, bets)
                return 200.0

        # Big and small blind
        bets = {"player-3": 100, "player-4": 200}

        best_player = bet_rounder.bet_round("player-1", bets, bet_function_mock)

        self.assertEquals(9, bet_calls["counter"])

        self.assertEquals(1000.0, player1.money)
        self.assertFalse(game_players.is_active("player-1"))

        self.assertEquals(800.0, player2.money)
        self.assertFalse(game_players.is_active("player-2"))

        self.assertEquals(0.0, player3.money)
        self.assertTrue(game_players.is_active("player-3"))

        self.assertEquals(0.0, player4.money)
        self.assertTrue(game_players.is_active("player-4"))

        self.assertEquals("player-3", best_player.id)
        self.assertEquals({"player-1": 0.0, "player-2": 200.0, "player-3": 1000.0, "player-4": 1000.0}, bets)

    def test_bet_round_one_player_only(self):
        game_players = GamePlayers([
            Player("player-1", "Player One", 500.0),
            Player("player-2", "Player Two", 1000.0),
            Player("player-3", "Player Three", 1000.0),
            Player("player-4", "Player Four", 2000.0),
        ])

        game_players.fold("player-1")
        game_players.fold("player-3")
        game_players.fold("player-4")

        bet_rounder = GameBetRounder(game_players)

        bet_calls = {  # Workaround as Python 2.7 doesn't have nonlocal
            "counter": 0
        }

        def bet_function_mock(player, min_bet, max_bet, bets):
            bet_calls["counter"] += 1
            return -1

        bets = {}

        best_player = bet_rounder.bet_round("player-2", bets, bet_function_mock)

        self.assertEquals(0, bet_calls["counter"])

        self.assertEquals("player-2", best_player.id)
        self.assertEquals({"player-2": 0.0}, bets)

    def test_bet_round_no_players(self):
        game_players = GamePlayers([
            Player("player-1", "Player One", 500.0),
            Player("player-2", "Player Two", 1000.0),
            Player("player-3", "Player Three", 1000.0),
            Player("player-4", "Player Four", 2000.0),
        ])

        game_players.fold("player-1")
        game_players.fold("player-2")
        game_players.fold("player-3")
        game_players.fold("player-4")

        bet_rounder = GameBetRounder(game_players)

        def bet_function_mock(player, min_bet, max_bet, bets):
            return -1

        bets = {}

        self.assertRaises(GameError, bet_rounder.bet_round, "player-2", bets, bet_function_mock)

    def test_bet_round_invalid_bet_dictionary(self):
        bets = {
            "player-1": 1000,
            "player-2": 300
        }

        game_players = GamePlayers([
            Player("player-1", "Player One", 1000.0),
            Player("player-2", "Player Two", 1000.0),
            Player("player-3", "Player Three", 1000.0),
            Player("player-4", "Player Four", 1000.0),
        ])

        def bet_function_mock(player, min_bet, max_bet, bets):
            return -1

        bet_rounder = GameBetRounder(game_players)

        self.assertRaises(ValueError, bet_rounder.bet_round, "player-3", bets, bet_function_mock)

    def test_bet_round_invalid_bet_dictionary_with_dealer(self):
        bets = {
            "player-1": 400,
            "player-2": 1000
        }

        game_players = GamePlayers([
            Player("player-1", "Player One", 1000.0),
            Player("player-2", "Player Two", 1000.0),
            Player("player-3", "Player Three", 1000.0),
            Player("player-4", "Player Four", 1000.0),
        ])

        def bet_function_mock(player, min_bet, max_bet, bets):
            return -1

        bet_rounder = GameBetRounder(game_players)

        self.assertRaises(ValueError, bet_rounder.bet_round, "player-4", bets, bet_function_mock)

    def test_bet_round_valid_bet_dictionary_1(self):
        bets = {
            "player-1": 400,
            "player-2": 1000
        }

        game_players = GamePlayers([
            Player("player-1", "Player One", 1000.0),
            Player("player-2", "Player Two", 1000.0),
            Player("player-3", "Player Three", 1000.0),
            Player("player-4", "Player Four", 1000.0),
        ])

        game_players.fold("player-3")

        def bet_function_mock(player, min_bet, max_bet, bets):
            return -1

        bet_rounder = GameBetRounder(game_players)

        bet_rounder.bet_round("player-4", bets, bet_function_mock)

    def test_bet_round_valid_bet_dictionary_2(self):
        bets = {
            "player-1": 400,
            "player-2": 1000
        }

        game_players = GamePlayers([
            Player("player-1", "Player One", 1000.0),
            Player("player-2", "Player Two", 1000.0)
        ])

        def bet_function_mock(player, min_bet, max_bet, bets):
            return -1

        bet_rounder = GameBetRounder(game_players)

        bet_rounder.bet_round("player-1", bets, bet_function_mock)


class GameBetHandlerTest(unittest.TestCase):
    pass


class GameTest(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()
