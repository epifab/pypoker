from . import ChannelError, MessageFormatError, MessageTimeout, DeckFactory, TraditionalPokerScoreDetector
from poker_game import PokerGame, GameFactory, EndGameException, GameError, GamePlayers, GameEventDispatcher
import gevent
import time
import uuid


class DeadHandException(Exception):
    pass


class TraditionalPokerGameFactory(GameFactory):
    def __init__(self, blind, logger):
        self._blind = blind
        self._logger = logger

    def create_game(self, players):
        # In a traditional poker game, the lowest rank is 9 with 2 players, 8 with three, 7 with four, 6 with five
        lowest_rank = 11 - len(players)
        game_id = str(uuid.uuid4())

        return TraditionalPokerGame(
            self._blind,
            id=game_id,
            game_players=GamePlayers(players),
            event_dispatcher=TraditionalPokerGameEventDispatcher(game_id=game_id, logger=self._logger),
            deck_factory=DeckFactory(lowest_rank),
            score_detector=TraditionalPokerScoreDetector(lowest_rank)
        )


class TraditionalPokerGameEventDispatcher(GameEventDispatcher):
    def new_game_event(self, game_id, players, dealer_id, blind_bets):
        self.raise_event(
            "new-game",
            {
                "game_id": game_id,
                "game_type": "traditional",
                "players": [player.dto() for player in players],
                "dealer_id": dealer_id,
                "blind_bets": blind_bets,
            }
        )

    def game_over_event(self):
        self.raise_event(
            "game-over",
            {}
        )

    def change_cards_action_event(self, player, timeout, timeout_epoch):
        self.raise_event(
            "player-action",
            {
                "action": "cards-change",
                "player": player.dto(),
                "timeout": timeout,
                "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
            }
        )
    
    def change_cards_event(self, player, num_cards):
        self.raise_event(
            "cards-change",
            {
                "player": player.dto(),
                "num_cards": num_cards
            }
        )


class TraditionalPokerGame(PokerGame):
    TIMEOUT_TOLERANCE = 2
    BET_TIMEOUT = 30
    CHANGE_CARDS_TIMEOUT = 30

    # WAIT_AFTER_CARDS_ASSIGNMENT = 1
    # WAIT_AFTER_BET_ROUND = 1
    # WAIT_AFTER_SHOWDOWN = 2
    # WAIT_AFTER_WINNER_DESIGNATION = 5

    WAIT_AFTER_CARDS_CHANGE = 1

    def __init__(self, blind, *args, **kwargs):
        PokerGame.__init__(self, *args, **kwargs)
        self._blind = blind

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Blinds
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _collect_blinds(self):
        # Kicking out players with no money
        for player in self._game_players.active:
            if player.money < self._blind:
                self._event_dispatcher.dead_player_event(player)
                self._game_players.remove(player.id)

        if self._game_players.count_active() < 2:
            raise GameError("Not enough players")

        bets = {}
        # In the traditional poker, the blind is collected from every player
        for player in self._game_players.active:
            player.take_money(self._blind)
            bets[player.id] = self._blind

        return bets

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Cards handler
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _change_cards_round(self, dealer_id, deck, scores):
        for player in self._game_players.round(dealer_id):
            timeout_epoch = time.time() + self.CHANGE_CARDS_TIMEOUT

            self._event_dispatcher.change_cards_action_event(player, self.CHANGE_CARDS_TIMEOUT, timeout_epoch)

            try:
                # Ask remote player to change cards
                discard = self._get_player_discard(player, scores, timeout_epoch=timeout_epoch + self.TIMEOUT_TOLERANCE)

            except (ChannelError, MessageFormatError, MessageTimeout) as e:
                player.send_message({"message_type": "error", "error": e.args[0]})
                self._event_dispatcher.dead_player_event(player)
                self._game_players.remove(player.id)

            else:
                if discard:
                    # Assign cards to the remote player
                    new_cards = deck.pop_cards(len(discard))
                    deck.push_cards(discard)
                    cards = [card for card in scores.player_cards(player.id) if card not in discard] + new_cards
                    scores.assign_cards(player.id, cards)
                    self._send_player_score(player, scores)

                self._event_dispatcher.change_cards_event(player, len(discard))
        gevent.sleep(self.WAIT_AFTER_CARDS_CHANGE)

    def _get_player_discard(self, player, scores, timeout_epoch):
        message = player.recv_message(timeout_epoch=timeout_epoch)

        MessageFormatError.validate_message_type(message, "cards-change")

        if "cards" not in message:
            raise MessageFormatError(attribute="cards", desc="Attribute is missing")

        discard_keys = message["cards"]

        try:
            # Removing duplicates
            discard_keys = list(set(discard_keys))
            if len(discard_keys) > 4:
                raise MessageFormatError(attribute="cards", desc="Maximum number of cards exceeded")
            player_cards = scores.player_cards(player.id)
            return [player_cards[key] for key in discard_keys]

        except (TypeError, IndexError):
            raise MessageFormatError(attribute="cards", desc="Invalid list of cards")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Game logic
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def play_hand(self, dealer_id):

        def detect_game_over():
            if self._game_players.count_active() < 2:
                raise EndGameException

        self._game_players.reset()
        deck = self._deck_factory.create_deck()
        scores = self._create_scores()
        pots = self._create_pots()

        blind_bets = self._collect_blinds()

        self._event_dispatcher.new_game_event(self._id, self._game_players.active, dealer_id, blind_bets)

        try:
            # In the traditional poker game, the blinds are immediately collected
            pots.add_bets(blind_bets)
            self._event_dispatcher.pots_update_event(self._game_players.active, pots)

            # Cards assignment
            self._assign_cards(5, dealer_id, deck, scores)

            # First bet round
            self._bet_handler.bet_round(dealer_id, {}, pots)
            detect_game_over()

            # Change cards
            self._change_cards_round(dealer_id, deck, scores)
            detect_game_over()

            if self._game_players.count_active_with_money() > 1:
                self._bet_handler.bet_round(dealer_id, {}, pots)
                detect_game_over()

            self._showdown(scores)
            raise EndGameException

        except EndGameException:
            self._detect_winners(pots, scores)

        finally:
            self._event_dispatcher.game_over_event()
