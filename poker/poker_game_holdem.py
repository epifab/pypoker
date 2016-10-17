from . import DeckFactory, HoldemPokerScoreDetector
from poker_game import PokerGame, GameFactory, GameError, EndGameException, GamePlayers, GameEventDispatcher
import gevent


class HoldemPokerGameFactory(GameFactory):
    def __init__(self, big_blind, small_blind):
        self._big_blind = big_blind
        self._small_blind = small_blind

    def create_game(self, players):
        return HoldemPokerGame(
            self._big_blind,
            self._small_blind,
            game_players=GamePlayers(players),
            event_dispatcher=HoldemPokerGameEventDispatcher(),
            deck_factory=DeckFactory(2),
            score_detector=HoldemPokerScoreDetector()
        )


class HoldemPokerGameEventDispatcher(GameEventDispatcher):
    def new_game_event(self, game_id, players, dealer_id, blind_bets):
        self.raise_event(
            "new-game",
            {
                "game_id": game_id,
                "game_type": "texas-holdem",
                "player_ids": [player.id for player in players],
                "dealer_id": dealer_id,
                "blind_bets": blind_bets
            }
        )

    def game_over_event(self):
        self.raise_event(
            "game-over",
            {}
        )

    def shared_cards_event(self, cards):
        self.raise_event(
            "shared-cards",
            {
                "cards": [card.dto() for card in cards]
            }
        )


class HoldemPokerGame(PokerGame):
    TIMEOUT_TOLERANCE = 2
    BET_TIMEOUT = 30

    WAIT_AFTER_CARDS_ASSIGNMENT = 0
    WAIT_AFTER_BET = 2
    WAIT_AFTER_WINNER_DESIGNATION = 5
    WAIT_AFTER_HAND = 0

    def __init__(self, big_blind, small_blind, *args, **kwargs):
        PokerGame.__init__(self, *args, **kwargs)
        self._big_blind = big_blind
        self._small_blind = small_blind

    def _add_shared_cards(self, new_shared_cards, scores):
        self._event_dispatcher.shared_cards_event(new_shared_cards)
        # Adds the new shared cards
        scores.add_shared_cards(new_shared_cards)
        # Broadcasts players their up-to-date score
        for player in self._game_players.active:
            self._send_player_score(player, scores)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Blinds
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _collect_blinds(self, dealer_id):
        # Kicking out players with no money
        for player in self._game_players.active:
            if player.money < self._big_blind:
                self._event_dispatcher.dead_player_event(player)
                self._game_players.remove(player.id)

        if self._game_players.count_active() < 2:
            raise GameError("Not enough players")

        active_players = list(self._game_players.round(dealer_id))

        bb_player = active_players[-1]
        bb_player.take_money(self._big_blind)

        sb_player = active_players[-2]
        sb_player.take_money(self._small_blind)

        return {
            bb_player.id: self._big_blind,
            sb_player.id: self._small_blind
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Game logic
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def play_hand(self, dealer_id):

        def bet_rounder(dealer_id, pots, scores, blind_bets):
            skip_next_rounds = False
            bets = blind_bets

            while True:
                if skip_next_rounds:
                    yield False

                # Bet round
                self._bet_handler.bet_round(dealer_id, bets, pots)
                gevent.sleep(self.WAIT_AFTER_BET)

                # Only the pre-flop bet has blind bets
                bets = {}

                # Not fun to play alone
                if self._game_players.count_active() < 2:
                    raise EndGameException

                # If everyone is all-in (possibly except 1 player) then showdown and skip next bet rounds
                skip_next_rounds = self._game_players.count_active_with_money() < 2
                if skip_next_rounds:
                    self._showdown(scores)

                yield skip_next_rounds

        # Initialization
        self._game_players.reset()
        deck = self._deck_factory.create_deck()
        scores = self._create_scores()
        pots = self._create_pots()

        # Collecting small and big blinds
        blind_bets = self._collect_blinds(dealer_id)

        # Initializing a bet rounder
        bet_rounds = bet_rounder(dealer_id, pots, scores, blind_bets)

        self._event_dispatcher.new_game_event(self._id, self._game_players.active, dealer_id, blind_bets)

        # Cards assignment
        self._assign_cards(2, dealer_id, deck, scores)
        gevent.sleep(self.WAIT_AFTER_CARDS_ASSIGNMENT)

        try:
            # Pre-flop bet round
            bet_rounds.next()

            # Flop
            self._add_shared_cards(deck.pop_cards(3), scores)
            gevent.sleep(self.WAIT_AFTER_CARDS_ASSIGNMENT)

            # Flop bet round
            bet_rounds.next()

            # Turn
            self._add_shared_cards(deck.pop_cards(1), scores)
            gevent.sleep(self.WAIT_AFTER_CARDS_ASSIGNMENT)

            # Turn bet round
            bet_rounds.next()

            # River
            self._add_shared_cards(deck.pop_cards(1), scores)
            gevent.sleep(self.WAIT_AFTER_CARDS_ASSIGNMENT)

            # River bet round
            bet_rounds.next()

            raise EndGameException

        except EndGameException:
            if self._game_players.count_active() > 1:
                self._showdown(scores)
            self._detect_winners(pots, scores)
            gevent.sleep(self.WAIT_AFTER_HAND)

        self._event_dispatcher.game_over_event()
