from . import Game, GameFactory, Card, Deck, ScoreDetector, EndGameException, \
    ChannelError, MessageTimeout, MessageFormatError
import gevent
import time
import logging


class DeadHandException(Exception):
    pass


class TraditionalPokerGameFactory(GameFactory):
    def __init__(self, blind=10.0, logger=None):
        self._blind = blind
        self._logger = logger if logger else logging

    def create_game(self, players, dealer_id):
        # In a traditional poker game, the lowest rank is 9 with 2 players, 8 with three, 7 with four, 6 with five
        lowest_rank = 11 - len(players)

        return TraditionalPokerGame(
            players=players,
            dealer_id=dealer_id,
            deck=Deck(lowest_rank),
            score_detector=ScoreDetector(lowest_rank),
            blind=self._blind,
            logger=self._logger
        )


class TraditionalPokerGame(Game):
    def __init__(self, players, deck, score_detector, blind=10.0, dealer_id=None, logger=None):
        Game.__init__(
            self,
            score_detector=score_detector,
            players=players,
            dealer_id=dealer_id,
            logger=logger
        )
        self._deck = deck
        # List of minimum scores required for very first bet (pair of J, Q, K, A)
        self._min_opening_scores = [score_detector.get_score([Card(r, 0), Card(r, 1)]) for r in [11, 12, 13, 14]]
        # Players whose score exceed the minimum opening score required for the current hand
        self._player_ids_allowed_to_open = set()
        # Players who must show their cards at the end of the game
        self._player_ids_show_cards = set()
        # The amount to collect for each player at the beginning of any game
        self._blind = blind
        # Number of consecutive dead hands
        self._dead_hands_counter = 0

    def _collect_blinds(self):
        # In the traditional poker, the blind is collected from every player
        for player_id in self._player_ids:
            if player_id not in self._folder_ids:
                player = self._players[player_id]
                if player.money < self._blind + 1.0:
                    self._add_dead_player(player_id, "Not enough money to play this hand")
                else:
                    player.take_money(self._blind)
                    self._bets[player_id] = self._blind
        self._recalculate_pots()

    def _assign_cards(self):
        min_opening_score = self._min_opening_scores[self._dead_hands_counter % len(self._min_opening_scores)]

        # Assign cards
        for player_id, player in self._active_players_round(self._dealer_id):
            # Distribute cards
            cards = self._deck.get_cards(5)
            score = self._score_detector.get_score(cards)
            if score.cmp(min_opening_score) >= 0:
                self._player_ids_allowed_to_open.add(player_id)

            try:
                player.set_cards(score.get_cards(), score)
                self.init_player_hand(player)
            except ChannelError as e:
                self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
                self._add_dead_player(player_id, e.args[0])

        self._raise_event(Game.Event.CARDS_ASSIGNMENT, {"min_opening_score": min_opening_score.dto()})

    def _player_opening_bet(self, player_id, min_bet, max_bet):
        try:
            player = self._players[player_id]
            timeout_epoch = time.time() + self.BET_TIMEOUT

            self._logger.info("{}: {} betting...".format(self, player))
            self._raise_event(
                Game.Event.PLAYER_ACTION,
                {
                    "action": "bet",
                    "min_bet": min_bet,
                    "max_bet": max_bet,
                    "opening": True,
                    "player_id": player_id,
                    "timeout": self.BET_TIMEOUT,
                    "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
                }
            )

            bet = self._get_player_bet(
                player,
                min_bet=min_bet,
                max_bet=max_bet,
                timeout_epoch=timeout_epoch + self.TIMEOUT_TOLERANCE
            )

            bet_type = None

            if bet == -1 or player_id not in self._player_ids_allowed_to_open:
                bet_type = "pass"
            elif bet == 0:
                bet_type = "check"
            else:
                player.take_money(bet)
                self._bets[player_id] += bet

                if not player.money:
                    bet_type = "all-in"
                else:
                    bet_type = "raise"

            self._logger.info("{}: {} bet: {} ({})".format(self, player, bet, bet_type))
            self._raise_event(
                Game.Event.BET,
                {
                    "event": "bet",
                    "bet": bet,
                    "bet_type": bet_type,
                    "player_id": player_id
                }
            )

            return bet, bet_type

        except (ChannelError, MessageFormatError, MessageTimeout) as e:
            self._add_dead_player(player_id, e.args[0])
            return -1, "fold"

    def _opening_bet_round(self):
        bets = {player_id: 0.0 for player_id in self._player_ids}

        # Bet round
        for player_id, player in self._active_players_round(self._dealer_id):
            min_bet = 1.0
            max_bet = self._get_max_bet(player_id, bets)

            # Ask remote player to bet
            bet, _ = self._player_opening_bet(player_id=player_id, min_bet=min_bet, max_bet=max_bet)

            if player_id in self._player_ids_allowed_to_open and bet != -1:
                return self._bet_round(
                    dealer_id=self._next_active_player_id(player_id),
                    bets={player_id: bet}
                )

        # Nobody opened
        self._folder_ids = set(self._player_ids)
        raise DeadHandException()

    def _change_cards(self):
        for player_id, player in self._active_players_round(self._dealer_id):
            try:
                timeout_epoch = time.time() + self.CHANGE_CARDS_TIMEOUT
                self._logger.info("{}: {} changing cards...".format(self, player))
                self._raise_event(
                    Game.Event.PLAYER_ACTION,
                    {
                        "action": "change-cards",
                        "player_id": player_id,
                        "timeout": self.CHANGE_CARDS_TIMEOUT,
                        "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
                    }
                )

                # Ask remote player to change cards
                discard = self._get_player_discard(player, timeout_epoch=timeout_epoch + Game.TIMEOUT_TOLERANCE)

                if discard:
                    # Assign cards to the remote player
                    new_cards = self._deck.get_cards(len(discard))
                    self._deck.add_discards(discard)
                    cards = [card for card in player.cards if card not in discard] + new_cards
                    score = self._score_detector.get_score(cards)
                    # Sending cards to the remote player
                    player.set_cards(score.get_cards(), score)
                    self.init_player_hand(player)

                self._logger.info("{}: {} changed {} cards".format(self, player, len(discard)))
                self._raise_event(Game.Event.CARDS_CHANGE, {"player_id": player_id, "num_cards": len(discard)})

            except (ChannelError, MessageFormatError, MessageTimeout) as e:
                self._add_dead_player(player_id, e.args[0])

    def _get_player_discard(self, player, timeout_epoch):
        """Gives players the opportunity to change some of their cards.
        Returns a tuple: (discard card keys, discard)."""
        message = player.recv_message(timeout_epoch=timeout_epoch)
        if "message_type" not in message:
            raise MessageFormatError(attribute="message_type", desc="Attribute missing")

        MessageFormatError.validate_message_type(message, "change-cards")

        if "cards" not in message:
            raise MessageFormatError(attribute="cards", desc="Attribute is missing")

        discard_keys = message["cards"]

        try:
            # removing duplicates
            discard_keys = sorted(set(discard_keys))
            if len(discard_keys) > 4:
                raise MessageFormatError(attribute="cards", desc="Maximum number of cards exceeded")
            player_cards = player.cards
            return [player_cards[key] for key in discard_keys]

        except (TypeError, IndexError):
            raise MessageFormatError(attribute="cards", desc="Invalid list of cards")

    def init_player_hand(self, player):
        score = player.score
        player.send_message({
            "message_type": "set-cards",
            "cards": [c.dto() for c in score.get_cards()],
            "score": {
                "cards": [c.dto() for c in score.get_cards()],
                "category": score.get_category()
            },
            "allowed_to_open": player.id in self._player_ids_allowed_to_open
        })

    def play_hand(self):
        try:
            # Initialization
            self._deck.initialize()
            self._player_ids_allowed_to_open = set()

            self._check_active_players()

            # Initial bet for every player
            self._collect_blinds()

            # Cards assignment
            self._logger.info("{}: [[cards assignment]]".format(self))
            self._assign_cards()
            gevent.sleep(Game.WAIT_AFTER_CARDS_ASSIGNMENT)

            try:
                # Opening bet round
                self._logger.info("{}: [[opening bet round]]".format(self))
                player_id = self._opening_bet_round()
                gevent.sleep(Game.WAIT_AFTER_BET)

            except DeadHandException:
                # Automatically play another hand if the last has failed
                self._logger.info("{}: dead hand".format(self))
                self._raise_event(Game.Event.DEAD_HAND)

                self._dead_hands_counter += 1

                self._folder_ids = set(self._dead_player_ids)
                self._dealer_id = self._next_active_player_id(self._dealer_id)

                gevent.sleep(Game.WAIT_AFTER_HAND)

                self.play_hand()  # Play another hand with the same players
                return  # Ensure no more code is executed

            else:
                # Cards change
                self._logger.info("{}: [[change cards]]".format(self))
                self._change_cards()
                gevent.sleep(Game.WAIT_AFTER_CARDS_CHANGE)

                # Final bet round
                self._logger.info("{}: [[final bet round]]".format(self))
                self._bet_round(player_id, {})
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
        }

        for player_id in self._player_ids:
            player = self._players[player_id]

            player_dto = player.dto(with_score=player_id in self._player_ids_show_cards)
            player_dto["alive"] = player_id not in self._folder_ids
            player_dto["bet"] = self._bets[player_id]

            game_dto["players"][player_id] = player_dto

        return game_dto
