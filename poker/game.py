from . import Card, ChannelError, MessageTimeout, MessageFormatError
import gevent
import logging
import time
import uuid


class GameError(Exception):
    pass


class DeadHandException(Exception):
    pass


class WinnerDetection(Exception):
    pass


class Game:
    WAIT_AFTER_HAND = 6
    WAIT_AFTER_CARDS_ASSIGNMENT = 1
    WAIT_AFTER_OPENING_BET = 0
    WAIT_AFTER_CARDS_CHANGE = 0
    WAIT_AFTER_FINAL_BET = 2

    CHANGE_CARDS_TIMEOUT = 45
    BET_TIMEOUT = 45
    TIMEOUT_TOLERANCE = 2

    class Event:
        new_game = "new-game"
        game_over = "game-over"
        cards_assignment = "cards-assignment"
        player_action = "player-action"
        dead_player = "dead-player"
        bet = "bet"
        cards_change = "cards-change"
        dead_hand = "dead-hand"
        winner_designation = "winner-designation"

    class EventListener:
        def game_event(self, event, event_data, game_data):
            raise NotImplemented

    def __init__(self, players, deck, score_detector, stake=10.0, logger=None):
        self._id = str(uuid.uuid4())
        # Dictionary of players keyed by their ids
        self._players = {player.get_id(): player for player in players}
        self._deck = deck
        self._score_detector = score_detector
        self._stake = stake
        self._logger = logger if logger else logging
        # List of player ids sorted according to the original players list
        self._player_ids = [player.get_id() for player in players]
        # Current dealer
        self._dealer_id = self._player_ids[0]
        # Players who fold
        self._folder_ids = set()
        # Players who timed out or died
        self._dead_player_ids = set()
        # Players whose score exceed the minimum opening score required for the current hand
        self._player_ids_allowed_to_open = set()
        # Players who must show their cards after winner detection
        self._player_ids_show_cards = set()
        # Number of consecutive dead hands
        self._dead_hands_counter = 0
        # List of minimum scores required for very first bet (pair of J, Q, K, A)
        self._min_opening_scores = [score_detector.get_score([Card(r, 0), Card(r, 1)]) for r in [11, 12, 13, 14]]
        # Game event subscribers
        self._event_subscribers = set()
        # Current pot
        self._pot = 0.0
        # Current bets for each player (sum of _bets is always equal to _pot)
        self._bets = {player_id: 0.0 for player_id in self._player_ids}

    def __str__(self):
        return "game {}".format(self._id)

    def subscribe(self, subscriber):
        self._event_subscribers.add(subscriber)

    def unsubscribe(self, subscriber):
        self._event_subscribers.remove(subscriber)

    def play_game(self):
        self._raise_event(Game.Event.new_game)
        try:
            self._play_hand()
        finally:
            self._raise_event(Game.Event.game_over)

    def _play_hand(self):
        """Play a single hand."""
        try:
            # Initialization
            self._deck.initialize()
            self._folder_ids = set(self._dead_player_ids)
            self._player_ids_allowed_to_open = set()
            self._player_ids_show_cards = set()

            self._check_active_players()

            # Cards assignment
            self._logger.info("{}: [[cards assignment]]".format(self))
            self._assign_cards()
            gevent.sleep(Game.WAIT_AFTER_CARDS_ASSIGNMENT)

            # Opening bet round
            self._logger.info("{}: [[opening bet round]]".format(self))
            player_id = self._opening_bet_round()
            gevent.sleep(Game.WAIT_AFTER_OPENING_BET)

            # Cards change
            self._logger.info("{}: [[change cards]]".format(self))
            self._change_cards()
            gevent.sleep(Game.WAIT_AFTER_CARDS_CHANGE)

            # Final bet round
            self._logger.info("{}: [[final bet round]]".format(self))
            player_id = self._final_bet_round(player_id)
            gevent.sleep(Game.WAIT_AFTER_FINAL_BET)

            # Winner detection
            self._logger.info("{}: [[winner detection]]".format(self))
            self._detect_winner(player_id)

        except WinnerDetection as e:
            winner_id = e.args[0]
            # Winner and hand finalization
            winner = self._players[winner_id]
            winner.set_money(winner.get_money() + self._pot)

            # Re-initialize pot, bets and move to the next dealer
            self._pot = 0.0
            self._bets = {player_id: 0.0 for player_id in self._player_ids}
            self._dealer_id = self._next_player_id(self._dealer_id)

            self._dead_hands_counter = 0
            self._logger.info("{}: {} won".format(self, winner))
            self._raise_event(Game.Event.winner_designation, {"player_id": winner_id})

            gevent.sleep(Game.WAIT_AFTER_HAND)

        except DeadHandException:
            # Automatically play another hand if the last has failed
            self._dead_hands_counter += 1
            self._logger.info("{}: dead hand".format(self))
            self._raise_event(Game.Event.dead_hand)

            gevent.sleep(Game.WAIT_AFTER_HAND)
            self._play_hand()

    def _assign_cards(self):
        # Define the minimum score to open
        min_opening_score = self._min_opening_scores[self._dead_hands_counter % len(self._min_opening_scores)]

        # Assign cards
        for player_id, player in self._players_round(self._dealer_id):
            # Collect stakes
            self._pot += self._stake
            self._bets[player_id] += self._stake
            player.set_money(player.get_money() - self._stake)
            # Distribute cards
            cards = self._deck.get_cards(5)
            score = self._score_detector.get_score(cards)
            if score.cmp(min_opening_score) >= 0:
                self._player_ids_allowed_to_open.add(player_id)

            try:
                player.set_cards(score.get_cards(), score)
                player.send_message({
                    "msg_id": "set-cards",
                    "cards": [c.dto() for c in score.get_cards()],
                    "score": {
                        "cards": [c.dto() for c in score.get_cards()],
                        "category": score.get_category()
                    },
                    "allowed_to_open": player_id in self._player_ids_allowed_to_open
                })
            except ChannelError as e:
                self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
                self._add_dead_player(player_id, e)

        self._raise_event(Game.Event.cards_assignment, {"min_opening_score": min_opening_score.dto()})

    def _opening_bet_round(self):
        # Bet round
        for player_id, player in self._players_round(self._dealer_id):
            # Ask remote player to bet
            bet, _ = self._bet(player_id=player_id, min_bet=1.0, max_bet=self._pot, opening=True)

            if player_id in self._player_ids_allowed_to_open and bet != -1:
                return self._bet_round(player_id, opening_bet=bet)

        # Nobody opened
        self._folder_ids = set(self._player_ids)
        raise DeadHandException()

    def _final_bet_round(self, best_player_id):
        return self._bet_round(best_player_id)

    def _bet_round(self, player_id, opening_bet=None):
        """Do a bet round. Returns the id of the player who made the strongest bet first.
        If opening_bet is specified, player_id is assumed to have made the opening bet already
        and the round will start from the player next to him."""

        bets = {player_id: 0.0 for player_id in self._player_ids}
        best_player_id = None

        if opening_bet:
            # player_id has already made an opening bet
            bets[player_id] = opening_bet
            best_player_id = player_id
            player_id = self._next_player_id(player_id)

        while player_id != best_player_id:
            if player_id not in self._folder_ids:
                if len(self._player_ids) - len(self._folder_ids) == 1:
                    # Only one player left, break and do not ask for a bet
                    # This can happen if during a bet round everybody fold and only the last player was left
                    return player_id

                # Two or more players still alive
                # Works out the minimum bet for the current player
                min_partial_bet = 0.0 if best_player_id is None else bets[best_player_id] - bets[player_id]

                # Bet
                current_bet, bet_type = self._bet(player_id=player_id, min_bet=min_partial_bet, max_bet=self._pot)

                if current_bet != -1:
                    bets[player_id] += current_bet

                    if best_player_id is None or bet_type == "raise":
                        best_player_id = player_id

            player_id = self._next_player_id(player_id)

        return best_player_id

    def _add_dead_player(self, player_id, exception):
        player = self._players[player_id]
        self._logger.info("{}: {} error: {}".format(self, player, exception.args[0]))
        player.try_send_message({"msg_id": "error", "error": exception.args[0]})
        self._dead_player_ids.add(player_id)
        self._raise_event(Game.Event.dead_player, {"player_id": player_id})
        self._add_folder(player_id)

    def _add_folder(self, player_id):
        self._folder_ids.add(player_id)
        self._check_active_players()

    def _check_active_players(self):
        active_player_ids = [player_id for player_id in self._player_ids if player_id not in self._folder_ids]
        if len(active_player_ids) == 0:
            raise GameError("No active players")
        elif len(active_player_ids) == 1:
            raise WinnerDetection(active_player_ids[0])

    def _players_round(self, start_player_id):
        """Iterate through a list of players who did not fold."""
        start_item = self._player_ids.index(start_player_id)

        for i in range(len(self._player_ids)):
            next_item = (i + start_item) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                yield player_id, self._players[player_id]
        raise StopIteration

    def _next_player_id(self, player_id):
        current_item = self._player_ids.index(player_id)
        next_item = (current_item + 1) % len(self._player_ids)
        return self._player_ids[next_item]

    def _change_cards(self):
        for player_id, player in self._players_round(self._dealer_id):
            try:
                timeout_epoch = time.time() + self.CHANGE_CARDS_TIMEOUT + self.TIMEOUT_TOLERANCE
                self._logger.info("{}: {} changing cards...".format(self, player))
                self._raise_event(
                    Game.Event.player_action,
                    {
                        "action": "change-cards",
                        "player_id": player_id,
                        "timeout": self.CHANGE_CARDS_TIMEOUT,
                        "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
                    }
                )

                # Ask remote player to change cards
                _, discards = self._change_player_cards(player, timeout_epoch=timeout_epoch)

                if discards:
                    # Assign cards to the remote player
                    new_cards = self._deck.get_cards(len(discards))
                    self._deck.add_discards(discards)
                    cards = [card for card in player.get_cards() if card not in discards] + new_cards
                    score = self._score_detector.get_score(cards)
                    # Sending cards to the remote player
                    player.set_cards(score.get_cards(), score)
                    player.send_message({
                        "msg_id": "set-cards",
                        "cards": [c.dto() for c in score.get_cards()],
                        "score": {
                            "cards": [c.dto() for c in score.get_cards()],
                            "category": score.get_category()
                        }
                    })

                self._logger.info("{}: {} changed {} cards".format(self, player, len(discards)))
                self._raise_event(Game.Event.cards_change, {"player_id": player_id, "num_cards": len(discards)})

            except (ChannelError, MessageFormatError, MessageTimeout) as e:
                self._add_dead_player(player_id, e)

    def _change_player_cards(self, player, timeout_epoch):
        """Gives players the opportunity to change some of their cards.
        Returns a tuple: (discard card keys, discard)."""
        message = player.recv_message(timeout_epoch=timeout_epoch)
        if "msg_id" not in message:
            raise MessageFormatError(attribute="msg_id", desc="Attribute missing")

        MessageFormatError.validate_msg_id(message, "change-cards")

        if "cards" not in message:
            raise MessageFormatError(attribute="cards", desc="Attribute is missing")

        discard_keys = message["cards"]

        try:
            # removing duplicates
            discard_keys = sorted(set(discard_keys))
            if len(discard_keys) > 4:
                raise MessageFormatError(attribute="cards", desc="Maximum number of cards exceeded")
            discard = [player._cards[key] for key in discard_keys]
            return discard_keys, discard

        except (TypeError, IndexError):
            raise MessageFormatError(attribute="cards", desc="Invalid list of cards")

    def _detect_winner(self, best_player_id):
        # Works out the winner
        winner = None
        for player_id, player in self._players_round(best_player_id):
            if not winner or player.get_score().cmp(winner.get_score()) > 0:
                winner = player
                self._player_ids_show_cards.add(player_id)
            else:
                self._add_folder(player_id)
                # In a real poker italian game this player is not obligated to show his score
        raise WinnerDetection(winner.get_id())

    def _bet(self, player_id, min_bet=0.0, max_bet=-1, opening=False):
        try:
            player = self._players[player_id]
            timeout_epoch = time.time() + self.BET_TIMEOUT + self.TIMEOUT_TOLERANCE

            self._logger.info("{}: {} betting...".format(self, player))
            self._raise_event(
                Game.Event.player_action,
                {
                    "action": "bet",
                    "min_bet": min_bet,
                    "max_bet": max_bet,
                    "opening": opening,
                    "player_id": player_id,
                    "timeout": self.BET_TIMEOUT,
                    "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
                }
            )

            bet = self._player_bet(
                player,
                min_bet=min_bet,
                max_bet=max_bet,
                opening=opening,
                timeout_epoch=timeout_epoch
            )
            bet_type = None

            if bet == -1 and opening:
                bet_type = "pass"
            elif bet == -1:
                bet_type = "fold"
            elif bet == 0:
                bet_type = "check"
            else:
                player.set_money(player.get_money() - bet)
                self._pot += bet
                self._bets[player_id] += bet
                if opening:
                    bet_type = "open"
                elif bet == min_bet:
                    bet_type = "call"
                else:
                    bet_type = "raise"

            self._logger.info("{}: {} bet: {} ({})".format(self, player, bet, bet_type))
            self._raise_event(
                Game.Event.bet,
                {
                    "event": "bet",
                    "bet": bet,
                    "bet_type": bet_type,
                    "player_id": player_id
                }
            )

            if bet_type == "fold":
                self._add_folder(player_id)

            return bet, bet_type

        except (ChannelError, MessageFormatError, MessageTimeout) as e:
            self._add_dead_player(player_id, e)
            return -1, "fold"

    def _player_bet(self, player, min_bet=0.0, max_bet=0.0, opening=False, timeout_epoch=None):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        message = player.recv_message(timeout_epoch=timeout_epoch)
        if "msg_id" not in message:
            raise MessageFormatError(attribute="msg_id", desc="Attribute missing")

        MessageFormatError.validate_msg_id(message, "bet")

        # No bet actually required (opening phase, score is too weak)
        if max_bet == -1:
            return -1

        if "bet" not in message:
            raise MessageFormatError(attribute="bet", desc="Attribute is missing")

        try:
            bet = float(message["bet"])

            # Fold
            if bet == -1.0:
                return bet

            # Bet range
            if bet < min_bet or bet > max_bet:
                raise MessageFormatError(
                    attribute="bet",
                    desc="Bet out of range. min: {} max: {}, actual: {}".format(min_bet, max_bet, bet))

            return bet

        except ValueError:
            raise MessageFormatError(attribute="bet", desc="'{}' is not a number".format(message.bet))

    def dto(self):
        game_dto = {
            "game_id": self._id,
            "players": {},
            "player_ids": self._player_ids,
            "pot": self._pot,
            "dealer_id": self._dealer_id
        }

        for player_id in self._player_ids:
            with_score = player_id in self._player_ids_show_cards
            player_dto = self._players[player_id].dto(with_score=with_score)
            player_dto.update({
                "alive": player_id not in self._folder_ids,
                "bet": self._bets[player_id],
            })
            game_dto["players"][player_id] = player_dto

        return game_dto

    def _raise_event(self, event, event_data=None):
        """Broadcast game events"""
        event_data = event_data if event_data else {}
        event_data["event"] = event
        game_data = self.dto()
        gevent.joinall([
            gevent.spawn(subscriber.game_event, event, event_data, game_data)
            for subscriber in self._event_subscribers
        ])
