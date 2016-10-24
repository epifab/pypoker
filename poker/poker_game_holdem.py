from . import DeckFactory, HoldemPokerScoreDetector
from poker_game import PokerGame, GameFactory, GameError, EndGameException, GamePlayers, GameEventDispatcher
import gevent
import uuid


class HoldemPokerGameFactory(GameFactory):
    def __init__(self, big_blind, small_blind, logger, game_subscribers=None):
        self._big_blind = big_blind
        self._small_blind = small_blind
        self._logger = logger
        self._game_subscribers = [] if game_subscribers is None else game_subscribers

    def create_game(self, players):
        game_id = str(uuid.uuid4())

        event_dispatcher = HoldemPokerGameEventDispatcher(game_id=game_id, logger=self._logger)
        for subscriber in self._game_subscribers:
            event_dispatcher.subscribe(subscriber)

        return HoldemPokerGame(
            self._big_blind,
            self._small_blind,
            id=game_id,
            game_players=GamePlayers(players),
            event_dispatcher=event_dispatcher,
            deck_factory=DeckFactory(2),
            score_detector=HoldemPokerScoreDetector()
        )


class HoldemPokerGameEventDispatcher(GameEventDispatcher):
    def new_game_event(self, game_id, players, dealer_id, big_blind, small_blind):
        self.raise_event(
            "new-game",
            {
                "game_id": game_id,
                "game_type": "texas-holdem",
                "players": [player.dto() for player in players],
                "dealer_id": dealer_id,
                "big_blind": big_blind,
                "small_blind": small_blind
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

    # WAIT_AFTER_CARDS_ASSIGNMENT = 1
    # WAIT_AFTER_BET_ROUND = 1
    # WAIT_AFTER_SHOWDOWN = 2
    # WAIT_AFTER_WINNER_DESIGNATION = 5

    WAIT_AFTER_FLOP_TURN_RIVER = 1

    def __init__(self, big_blind, small_blind, *args, **kwargs):
        PokerGame.__init__(self, *args, **kwargs)
        self._big_blind = big_blind
        self._small_blind = small_blind

    def _add_shared_cards(self, new_shared_cards, scores):
        self._event_dispatcher.shared_cards_event(new_shared_cards)
        # Adds the new shared cards
        scores.add_shared_cards(new_shared_cards)

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

        bets = {}

        sb_player = active_players[-2]
        sb_player.take_money(self._small_blind)
        bets[sb_player.id] = self._small_blind

        self._event_dispatcher.bet_event(
            player=sb_player,
            bet=self._small_blind,
            bet_type="blind",
            bets=bets
        )

        bb_player = active_players[-1]
        bb_player.take_money(self._big_blind)
        bets[bb_player.id] = self._big_blind

        self._event_dispatcher.bet_event(
            player=bb_player,
            bet=self._big_blind,
            bet_type="blind",
            bets=bets
        )

        return bets

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Game logic
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def play_hand(self, dealer_id):

        def bet_rounder(dealer_id, pots, scores, blind_bets):
            next_bet_round = True
            bets = blind_bets

            while True:
                if next_bet_round:
                    # Bet round
                    self._bet_handler.bet_round(dealer_id, bets, pots)

                    # Only the pre-flop bet has blind bets
                    bets = {}

                    # Not fun to play alone
                    if self._game_players.count_active() < 2:
                        raise EndGameException

                    # If everyone is all-in (possibly except 1 player) then showdown and skip next bet rounds
                    next_bet_round = self._game_players.count_active_with_money() > 1

                    # There won't be a next bet round: showdown
                    if not next_bet_round:
                        self._showdown(scores)

                yield next_bet_round

        # Initialization
        self._game_players.reset()
        deck = self._deck_factory.create_deck()
        scores = self._create_scores()
        pots = self._create_pots()

        self._event_dispatcher.new_game_event(
            game_id=self._id,
            players=self._game_players.active,
            dealer_id=dealer_id,
            big_blind=self._big_blind,
            small_blind=self._small_blind
        )

        try:
            # Collecting small and big blinds
            blind_bets = self._collect_blinds(dealer_id)

            # Initializing a bet rounder
            bet_rounds = bet_rounder(dealer_id, pots, scores, blind_bets)

            # Cards assignment
            self._assign_cards(2, dealer_id, deck, scores)

            # Pre-flop bet round
            bet_rounds.next()

            # Flop
            self._add_shared_cards(deck.pop_cards(3), scores)
            gevent.sleep(self.WAIT_AFTER_FLOP_TURN_RIVER)

            # Flop bet round
            bet_rounds.next()

            # Turn
            self._add_shared_cards(deck.pop_cards(1), scores)
            gevent.sleep(self.WAIT_AFTER_FLOP_TURN_RIVER)

            # Turn bet round
            bet_rounds.next()

            # River
            self._add_shared_cards(deck.pop_cards(1), scores)
            gevent.sleep(self.WAIT_AFTER_FLOP_TURN_RIVER)

            # River bet round
            if bet_rounds.next() and self._game_players.count_active() > 1:
                # There are still active players in the match and no showdown yet
                self._showdown(scores)

            raise EndGameException

        except EndGameException:
            self._detect_winners(pots, scores)

        finally:
            self._event_dispatcher.game_over_event()
