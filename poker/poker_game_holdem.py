from . import Game, GameFactory, Deck, ScoreDetector, EndGameException, ChannelError
import gevent
import logging


class HoldEmPokerGameFactory(GameFactory):
    def __init__(self, small_blind=10.0, big_blind=20.0, logger=None):
        self._small_blind = small_blind
        self._big_blind = big_blind
        self._logger = logger if logger else logging

    def create_game(self, players, dealer_id):
        return HoldEmPokerGame(
            players=players,
            dealer_id=dealer_id,
            deck=Deck(2),
            score_detector=ScoreDetector(2),
            small_blind=self._small_blind,
            big_blind=self._big_blind,
            logger=self._logger
        )


class HoldEmPokerGame(Game):
    def __init__(self, players, deck, score_detector, small_blind, big_blind, dealer_id=None, logger=None):
        Game.__init__(
            self,
            score_detector=score_detector,
            players=players,
            dealer_id=dealer_id,
            logger=logger
        )
        self._deck = deck
        # Players who must show their cards at the end of the game
        self._player_ids_show_cards = set()
        self._small_blind = small_blind
        self._big_blind = big_blind
        self._shared_cards = []

    def _collect_blinds(self):
        # Kicking out players with no money
        for player in self._players.values():
            if player.money < self._big_blind:
                self._add_dead_player(player.id, "Not enough money to play this hand")

        player_ids = [player_id for player_id, _ in self._active_players_round(self._dealer_id)]
        player_ids.reverse()

        self._players[player_ids[0]].take_money(self._big_blind)
        self._bets[player_ids[0]] -= self._big_blind

        self._players[player_ids[1]].take_money(self._small_blind)
        self._bets[player_ids[1]] -= self._small_blind

        self._recalculate_pots()

    def _assign_cards(self):
        # Assign cards
        for player_id, player in self._active_players_round(self._dealer_id):
            # Distribute cards
            cards = self._deck.pop_cards(2)
            score = self._score_detector.get_score(cards)

            try:
                player.set_cards(cards, score)
                self.init_player_hand(player)
            except ChannelError as e:
                self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
                self._add_dead_player(player_id, e.args[0])

        self._raise_event(Game.Event.CARDS_ASSIGNMENT)

    def init_player_hand(self, player):
        player.send_message({
            "message_type": "set-cards",
            "cards": [card.dto() for card in player.score.cards],
            "score": player.score.dto(),
        })

    def _add_shared_cards(self, number_of_cards):
        self._shared_cards.append(self._deck.pop_cards(number_of_cards))
        for player in self._players.values():
            cards = player.cards
            score = self._score_detector.get_score(cards + self._shared_cards)
            player.set_cards(cards, score)

    def play_hand(self):
        try:
            # Initialization
            self._deck.initialize()
            self._shared_cards = []

            self._check_active_players()

            # Initial bet for every player
            self._collect_blinds()

            # Cards assignment
            self._logger.info("{}: [[cards assignment]]".format(self))
            self._assign_cards()
            gevent.sleep(Game.WAIT_AFTER_CARDS_ASSIGNMENT)

            # Pre-flop
            self._logger.info("{}: [[pre-flop bet]]".format(self))
            self._bet_round(self._dealer_id, self._bets)
            gevent.sleep(Game.WAIT_AFTER_BET)

            # Flop
            self._logger.info("{}: [[flop]]".format(self))
            self._add_shared_cards(3)
            self._bet_round(self._dealer_id, self._bets)
            gevent.sleep(Game.WAIT_AFTER_BET)

            # Turn
            self._logger.info("{}: [[turn]]".format(self))
            self._add_shared_cards(1)
            self._bet_round(self._dealer_id, self._bets)
            gevent.sleep(Game.WAIT_AFTER_BET)

            # River
            self._logger.info("{}: [[river]]".format(self))
            self._add_shared_cards(1)
            self._bet_round(self._dealer_id, self._bets)
            gevent.sleep(Game.WAIT_AFTER_BET)

            # Winner detection
            raise EndGameException

        except EndGameException:
            self._logger.info("{}: [[winners detection]]".format(self))
            if len(self._player_ids) - len(self._folder_ids) > 1:
                self._player_ids_show_cards = set(
                    player_id
                    for player_id in self._player_ids
                    if player_id not in self._folder_ids
                )
            self._detect_winners()
            gevent.sleep(self.WAIT_AFTER_WINNER_DESIGNATION)
            self._folder_ids = set(self._dead_player_ids)
            self._dealer_id = self._next_active_player_id(self._dealer_id)
            gevent.sleep(self.WAIT_AFTER_HAND)

    def dto(self):
        game_dto = {
            "game_id": self._id,
            "players": {},
            "player_ids": self._player_ids,
            "pots": self._pots,
            "dealer_id": self._dealer_id,
            "shared_cards": [card.dto() for card in self._shared_cards],
        }

        for player in self._players.values():
            player_dto = player.dto(with_score=player.id in self._player_ids_show_cards)
            player_dto["alive"] = player.id not in self._folder_ids
            player_dto["bet"] = self._bets[player.id]
            game_dto["players"][player.id] = player_dto

        return game_dto
