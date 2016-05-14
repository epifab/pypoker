from . import Card, ChannelError, MessageTimeout, MessageFormatError
import logging
import time
import gevent


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
        bet = "bet"
        cards_change = "cards-change"
        dead_hand = "dead-hand"
        winner_designation = "winner-designation"

    def __init__(self, players, deck, score_detector, stake=10.0, logger=None):
        self._id = id(self)
        self._players = players
        self._deck = deck
        self._score_detector = score_detector
        self._stake = stake
        self._logger = logger if logger else logging
        # number of consecutive dead hands
        self._dead_hands = 0
        # current pot
        self._pot = 0.0
        # current bets for each player (sum of _bets is always equal to _pot)
        self._bets = [0.0] * len(players)
        self._dealer = 0
        # set of current hand folders
        self._folders = set()
        # players with a current score higher than current min opening score
        self._players_allowed_to_open = set()
        # players who have to show their cards after winner detection
        self._players_showing_cards = set()
        # players who timed out or died
        self._dead_players = set()
        # Pair of J, Q, K, A
        self._min_opening_scores = [score_detector.get_score([Card(r, 0), Card(r, 1)]) for r in [11, 12, 13, 14]]

    def __str__(self):
        return "game " + str(self._id)

    def play_game(self):
        self.broadcast({"event": Game.Event.new_game})
        while not self._dead_players:
            try:
                self.play_hand()
            except GameError:
                break
        self.broadcast({"event": Game.Event.game_over})

    def play_hand(self):
        """Play a single hand."""
        try:
            # Initialization
            self._deck.initialize()
            self._folders = set(self._dead_players)
            self._players_showing_cards = set()

            self._check_active_players()

            # Cards assignment
            self._assign_cards()
            gevent.sleep(Game.WAIT_AFTER_CARDS_ASSIGNMENT)

            # Opening bet round
            player_key = self._opening_bet_round()
            gevent.sleep(Game.WAIT_AFTER_OPENING_BET)

            # Cards change
            self._change_cards()
            gevent.sleep(Game.WAIT_AFTER_CARDS_CHANGE)

            # Final bet round
            player_key = self._final_bet_round(player_key)
            gevent.sleep(Game.WAIT_AFTER_FINAL_BET)

            # Winner detection
            self._detect_winner(player_key)

        except WinnerDetection as e:
            winner_key = e.args[0]
            # Winner and hand finalization
            winner = self._players[winner_key]
            winner.set_money(winner.get_money() + self._pot)

            # Re-initialize pot, bets and move to the next dealer
            self._pot = 0.0
            self._bets = [0.0] * len(self._players)
            self._dealer = self._next_player_key(self._dealer)

            self._dead_hands = 0
            self._logger.info("{}: {} won".format(self, winner))
            self.broadcast({
                "event": Game.Event.winner_designation,
                "player": winner_key})

            gevent.sleep(Game.WAIT_AFTER_HAND)

        except DeadHandException:
            # Automatically play another hand if the last has failed
            self._dead_hands += 1
            self._logger.info("{}: dead hand".format(self))
            self.broadcast({"event": Game.Event.dead_hand})

            gevent.sleep(Game.WAIT_AFTER_HAND)
            self.play_hand()

    def get_players(self):
        """Returns the list of players"""
        return self._players

    def _assign_cards(self):
        # Define the minimum score to open
        min_opening_score = self._min_opening_scores[self._dead_hands % len(self._min_opening_scores)]

        # Assign cards
        for player_key, player in self._players_round(self._dealer):
            # Collect stakes
            self._pot += self._stake
            self._bets[player_key] += self._stake
            player.set_money(player.get_money() - self._stake)
            # Distribute cards
            cards = self._deck.get_cards(5)
            score = self._score_detector.get_score(cards)
            if score.cmp(min_opening_score) >= 0:
                self._players_allowed_to_open.add(player_key)

            try:
                player.set_cards(score.get_cards(), score)
                player.send_message({
                    'msg_id': 'set-cards',
                    'cards': [c.dto() for c in score.get_cards()],
                    'score': {
                        'cards': [c.dto() for c in score.get_cards()],
                        'category': score.get_category()
                    },
                    'allowed_to_open': player_key in self._players_allowed_to_open
                })
            except ChannelError as e:
                self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
                self._add_dead_player(player_key, e)

        self.broadcast({"event": Game.Event.cards_assignment, "min_opening_score": min_opening_score.dto()})

    def _opening_bet_round(self):
        # Bet round
        for player_key, player in self._players_round(self._dealer):
            # Ask remote player to bet
            bet, _ = self._bet(player_key=player_key, min_bet=1.0, max_bet=self._pot, opening=True)

            if player_key in self._players_allowed_to_open and bet != -1:
                return self._bet_round(player_key, opening_bet=bet)

        # Nobody opened
        self._folders = set([k for (k, _) in enumerate(self._players)])
        raise DeadHandException()

    def _final_bet_round(self, best_player_key):
        return self._bet_round(best_player_key)

    def _bet_round(self, player_key, opening_bet=None):
        """Do a bet round. Returns the id of the player who made the strongest bet first.
        If opening_bet is specified, player_key is assumed to have made the opening bet already
        and the round will start from the player next to him."""

        bets = [0.0] * len(self._players)
        best_player_key = -1

        if opening_bet:
            # player_key has already made an opening bet
            bets[player_key] = opening_bet
            best_player_key = player_key
            player_key = self._next_player_key(player_key)

        while player_key != best_player_key:
            if player_key in self._folders:
                continue

            # Only one player left, break and do not ask for a bet
            # This can happen if during a bet round everybody fold and only the last player was left
            if len(self._players) - len(self._folders) == 1:
                return player_key

            # Two or more players still alive
            # Works out the minimum bet for the current player
            min_partial_bet = 0.0 if best_player_key == -1 else bets[best_player_key] - bets[player_key]

            # Bet
            current_bet, bet_type = self._bet(player_key=player_key, min_bet=min_partial_bet, max_bet=self._pot)

            if current_bet != -1:
                bets[player_key] += current_bet

                if best_player_key == -1 or bet_type == 'raise':
                    best_player_key = player_key

            player_key = self._next_player_key(player_key)

        return best_player_key

    def _add_dead_player(self, player_key, exception):
        player = self._players[player_key]
        self._logger.info("{}: {} error: {}".format(self, player, exception.args[0]))
        player.try_send_message({"msg_id": "error", "error": exception.args[0]})
        self._dead_players.add(player_key)
        self.broadcast({"msg_id": "dead-player", "player": player_key})
        self._add_folder(player_key)

    def _add_folder(self, player_key):
        self._folders.add(player_key)
        self._check_active_players()

    def _check_active_players(self):
        active_player_keys = [k for (k, _) in enumerate(self._players) if k not in self._folders]
        if len(active_player_keys) == 0:
            raise GameError("No active players")
        elif len(active_player_keys) == 1:
            raise WinnerDetection(active_player_keys[0])

    def _players_round(self, start_id=0):
        """Iterate through a list of players who did not fold."""
        for i in range(len(self._players)):
            player_key = (i + start_id) % len(self._players)
            if player_key not in self._folders:
                yield player_key, self._players[player_key]
        raise StopIteration

    def _next_player_key(self, index):
        return (index + 1) % len(self._players)

    def _change_cards(self):
        for player_key, player in self._players_round(self._dealer):
            try:
                timeout = time.time() + self.CHANGE_CARDS_TIMEOUT + self.TIMEOUT_TOLERANCE
                self._logger.info("{}: {} changing cards...".format(self, player))
                self.broadcast({
                    "event": "player-action",
                    "action": "change-cards",
                    "player": player_key,
                    "timeout": self.CHANGE_CARDS_TIMEOUT,
                    "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout))})

                # Ask remote player to change cards
                _, discards = self._change_player_cards(player, timeout=timeout)

                if discards:
                    # Assign cards to the remote player
                    new_cards = self._deck.get_cards(len(discards))
                    self._deck.add_discards(discards)
                    cards = [card for card in player.get_cards() if card not in discards] + new_cards
                    score = self._score_detector.get_score(cards)
                    # Sending cards to the remote player
                    player.set_cards(score.get_cards(), score)
                    player.send_message({
                        'msg_id': 'set-cards',
                        'cards': [c.dto() for c in score.get_cards()],
                        'score': {
                            'cards': [c.dto() for c in score.get_cards()],
                            'category': score.get_category()
                        }
                    })

                self._logger.info("{}: {} changed {} cards".format(self, player, len(discards)))
                self.broadcast({
                    "event": "cards-change",
                    "player": player_key,
                    "num_cards": len(discards)})

            except (ChannelError, MessageFormatError, MessageTimeout) as e:
                self._add_dead_player(player_key, e)

    def _change_player_cards(self, player, timeout):
        """Gives players the opportunity to change some of their cards.
        Returns a tuple: (discard card ids, discards)."""
        while True:
            message = player.recv_message(timeout=timeout)
            if "msg_id" not in message:
                raise MessageFormatError(attribute="msg_id", desc="Attribute missing")
            if message["msg_id"] != "ping":
                break

        MessageFormatError.validate_msg_id(message, "change-cards")

        if "cards" not in message:
            raise MessageFormatError(attribute="cards", desc="Attribute is missing")

        discard_keys = message["cards"]

        try:
            # removing duplicates
            discard_keys = sorted(set(discard_keys))
            if len(discard_keys) > 4:
                raise MessageFormatError(attribute="cards", desc="Maximum number of cards exceeded")
            discards = [player._cards[key] for key in discard_keys]
            return discard_keys, discards

        except (TypeError, IndexError):
            raise MessageFormatError(attribute="cards", desc="Invalid list of cards")

    def _detect_winner(self, best_player_key):
        # Works out the winner
        winner = None
        winner_key = -1
        for player_key, player in self._players_round(best_player_key):
            if not winner or player.get_score().cmp(winner.get_score()) > 0:
                winner = player
                winner_key = player_key
                self._players_showing_cards.add(player_key)
            else:
                self._add_folder(player_key)
                # In a real poker italian game this player is not obligated to show his score
        raise WinnerDetection(winner_key)

    def _bet(self, player_key, min_bet=0.0, max_bet=-1, opening=False):
        try:
            player = self._players[player_key]
            timeout = time.time() + self.BET_TIMEOUT + self.TIMEOUT_TOLERANCE

            self._logger.info("{}: {} betting...".format(self, player))
            self.broadcast({
                "event": "player-action",
                "action": "bet",
                "min_bet": min_bet,
                "max_bet": max_bet,
                "opening": opening,
                "player": player_key,
                "timeout": self.BET_TIMEOUT,
                "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout))})

            bet = self._player_bet(player, min_bet=min_bet, max_bet=max_bet, opening=opening, timeout=timeout)
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
                self._bets[player_key] += bet
                if opening:
                    bet_type = "open"
                elif bet == min_bet:
                    bet_type = "call"
                else:
                    bet_type = "raise"

            self._logger.info("{}: {} bet: {} ({})".format(self, player, bet, bet_type))
            self.broadcast({
                "event": "bet",
                "bet": bet,
                "bet_type": bet_type,
                "player": player_key})

            if bet_type == "fold":
                self._add_folder(player_key)

            return bet, bet_type

        except (ChannelError, MessageFormatError, MessageTimeout) as e:
            self._add_dead_player(player_key, e)
            return -1, "fold"

    def _player_bet(self, player, min_bet=0.0, max_bet=0.0, opening=False, timeout=None):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        player.send_message({
            "msg_id": "bet",
            "timeout": None if not timeout else time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout)),
            "min_bet": min_bet,
            "max_bet": max_bet,
            "opening": opening})

        while True:
            message = player.recv_message(timeout=timeout)
            if "msg_id" not in message:
                raise MessageFormatError(attribute="msg_id", desc="Attribute missing")
            if message["msg_id"] != "ping":
                # Ignore ping messages
                break

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
            "game": self._id,
            "pot": self._pot,
            "dealer": self._dealer,
            "players": []}

        for player_key, player in enumerate(self._players):
            with_score = player_key in self._players_showing_cards
            player_dto = player.dto(with_score=with_score)
            player_dto.update({
                "alive": player_key not in self._folders,
                "bet": self._bets[player_key],
            })
            game_dto["players"].append(player_dto)

        return game_dto

    def broadcast(self, message={}):
        """Sends a game-update message to every player"""
        message.update(self.dto())
        if "msg_id" not in message:
            message["msg_id"] = "game-update"
        for player in self._players:
            player.try_send_message(message)
