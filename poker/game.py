from . import Card, ChannelError, MessageTimeout, MessageFormatError
import logging
import random, string
import time
import gevent


class GameError(Exception):
    pass


class DeadHandException(Exception):
    pass


class Game:
    WAIT_AFTER_HAND = 10
    WAIT_AFTER_CARDS_ASSIGNMENT = 3
    WAIT_AFTER_BET = 2

    CHANGE_CARDS_TIMEOUT = 45
    BET_TIMEOUT = 45

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
        self._id = ''.join(random.choice(string.ascii_lowercase) for i in range(5))
        self._players = players
        self._deck = deck
        self._score_detector = score_detector
        self._stake = stake
        self._dead_hands = 0
        self._dealer_key = 0
        self._folder_keys = []
        self._public_cards_keys = []
        self._players_in_error = []
        self._pot = 0.0
        self._bets = [0.0] * len(players)
        # Pair of J, Q, K, A
        self._min_opening_scores = [score_detector.get_score([Card(r, 0), Card(r, 1)]) for r in [11, 12, 13, 14]]
        self._logger = logger if logger else logging

    def __str__(self):
        return "game " + self._id

    def play_game(self):
        self.broadcast({"event": Game.Event.new_game})
        while not self._players_in_error:
            try:
                self.play_hand()
            except GameError:
                break
        self.broadcast({"event": Game.Event.game_over})

    def play_hand(self):
        """Play a single hand."""
        while True:
            try:
                # Initialization
                self._deck.initialize()
                self._folder_keys = list(self._players_in_error)
                self._public_cards_keys = []

                alive_player_keys = [k for (k, _) in enumerate(self._players) if k not in self._folder_keys]

                if len(alive_player_keys) == 0:
                    raise GameError("Every player left the table")

                elif len(alive_player_keys) > 1:
                    # Cards assignment
                    self._assign_cards()
                    gevent.sleep(Game.WAIT_AFTER_CARDS_ASSIGNMENT)

                    # Opening
                    player_key = self._opening_bet_round()
                    gevent.sleep(Game.WAIT_AFTER_BET)

                    # 2 or more players alive
                    if len(self._players) - len(self._folder_keys) > 1:
                        self._change_cards()
                        gevent.sleep(Game.WAIT_AFTER_CARDS_ASSIGNMENT)
                        player_key = self._final_bet_round(player_key)
                        gevent.sleep(Game.WAIT_AFTER_BET)

                    # 2 or more players still alive
                    if len(self._players) - len(self._folder_keys) > 1:
                        player_key = self._detect_winner(player_key)

                elif len(alive_player_keys) == 1:
                    # Only 1 player alive
                    player_key = alive_player_keys[0]

                # Winner and hand finalization
                winner = self._players[player_key]
                winner.set_money(winner.get_money() + self._pot)

                # Re-initialize pot, bets and move to the next dealer
                self._pot = 0.0
                self._bets = [0.0] * len(self._players)
                self._dealer_key = (self._dealer_key + 1) % len(self._players)

                self._dead_hands = 0
                self._logger.info("{}: {} won".format(self, winner))
                self.broadcast({
                    "event": Game.Event.winner_designation,
                    "player": player_key})
                break

            except DeadHandException:
                # Automatically play another hand if the last has failed
                self._dead_hands += 1
                self._logger.info("{}: dead hand".format(self))
                self.broadcast({"event": Game.Event.dead_hand})
                continue

            finally:
                gevent.sleep(Game.WAIT_AFTER_HAND)

    def get_players(self):
        """Returns the list of players"""
        return self._players

    def _assign_cards(self):
        # Assign cards
        for player_key, player in self._players_round(self._dealer_key):
            # Collect stakes
            self._pot += self._stake
            self._bets[player_key] += self._stake
            player.set_money(player.get_money() - self._stake)
            # Distribute cards
            cards = self._deck.get_cards(5)
            score = self._score_detector.get_score(cards)

            try:
                player.set_cards(score.get_cards(), score)
            except ChannelError as e:
                self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
                self._add_faulty_player(player_key, e)

        self.broadcast({"event": "cards-assignment"})

    def _opening_bet_round(self):
        # Define the minimum score to open
        min_opening_score = self._min_opening_scores[self._dead_hands % len(self._min_opening_scores)]

        # Bet round
        for player_key, player in self._players_round(self._dealer_key):
            max_bet = -1 if player.get_score().cmp(min_opening_score) < 0 else self._pot

            # Ask remote player to bet
            bet, _ = self._bet(player_key=player_key, min_bet=1.0, max_bet=max_bet, opening=True)

            if bet != -1:
                return self._bet_round(player_key, opening_bet=bet)

        # Nobody opened
        self._folder_keys = [k for (k, _) in enumerate(self._players)]
        raise DeadHandException

    def _final_bet_round(self, best_player_key):
        return self._bet_round(best_player_key)

    def _bet_round(self, player_key, opening_bet=None):
        """Do a bet round. Returns the id of the player who made the strongest bet first.
        If opening_bet is specified, player_key is assumed to have made the opening bet already
        and the round will start from the player next to him."""

        # Not too fun if nobody is playing
        if len(self._players) == len(self._folder_keys):
            raise GameError("No players to gamble")

        bets = [0.0] * len(self._players)
        best_player_key = -1

        if opening_bet:
            # player_key has already made an opening bet
            bets[player_key] = opening_bet
            best_player_key = player_key
            player_key = (player_key + 1) % len(self._players)

        while player_key != best_player_key:
            # Exclude folders
            if player_key in self._folder_keys:
                continue

            # Only one player left, break and do not ask for a bet
            if len(self._players) - len(self._folder_keys) == 1:
                best_player_key = player_key
                break

            # Two or more players still alive
            # Works out the minimum bet for the current player
            min_partial_bet = 0.0 if best_player_key == -1 else bets[best_player_key] - bets[player_key]

            # Bet
            current_bet, bet_type = self._bet(player_key=player_key, min_bet=min_partial_bet, max_bet=self._pot)

            if current_bet != -1:
                bets[player_key] += current_bet

                if best_player_key == -1 or bet_type == 'raise':
                    best_player_key = player_key

            # Next player
            player_key = (player_key + 1) % len(self._players)

        return best_player_key

    def _add_faulty_player(self, player_key, exception):
        self._logger.info("{}: {} error: {}".format(self, self._players[player_key], exception.args[0]))
        self._players[player_key].try_send_message({"msg_id": "error", "error": exception.args[0]})
        self._folder_keys.append(player_key)
        self._players_in_error.append(player_key)
        self.broadcast({"msg_id": "dead-player", "player": player_key})

    def _players_round(self, start_id=0):
        """Iterate through a list of players who did not fold."""
        for i in range(len(self._players)):
            player_key = (i + start_id) % len(self._players)
            if player_key not in self._folder_keys:
                yield player_key, self._players[player_key]
        raise StopIteration

    def _change_cards(self):
        # Change cards
        for player_key, player in self._players_round(self._dealer_key):
            discards = []

            try:
                timeout = TimeoutGenerator.generate(self.CHANGE_CARDS_TIMEOUT)
                self._logger.info("{}: {} changing cards...".format(self, player))
                self.broadcast({
                    "event": "player-action",
                    "action": "change-cards",
                    "player": player_key,
                    "timeout": self.CHANGE_CARDS_TIMEOUT,
                    "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout))})

                # Ask remote player to change cards
                _, discards = player.change_cards(timeout=timeout)

                if discards:
                    # Assign cards to the remote player
                    new_cards = self._deck.get_cards(len(discards))
                    self._deck.add_discards(discards)
                    cards = [card for card in player.get_cards() if card not in discards] + new_cards
                    score = self._score_detector.get_score(cards)
                    # Sending cards to the remote player
                    player.set_cards(score.get_cards(), score)

            except (ChannelError, MessageFormatError, MessageTimeout) as e:
                self._add_faulty_player(player_key, e)

            finally:
                self._logger.info("{}: {} changed {} cards".format(self, player, len(discards)))
                self.broadcast({
                    "event": "cards-change",
                    "player": player_key,
                    "num_cards": len(discards)})

    def _detect_winner(self, best_player_key):
        # Works out the winner
        winner = None
        winner_key = -1
        for player_key, player in self._players_round(best_player_key):
            if not winner or player.get_score().cmp(winner.get_score()) > 0:
                winner = player
                winner_key = player_key
                self._public_cards_keys.append(player_key)
            else:
                self._folder_keys.append(player_key)
                # In a real poker italian game this player is not obligated to show his score
            self._logger.info("{}: {} score: {}".format(self, player, player.get_score()))
        return winner_key

    def _bet(self, player_key, min_bet=0.0, max_bet=-1, opening=False):
        bet = -1
        bet_type = "pass" if opening else "fold"

        try:
            player = self._players[player_key]
            timeout = TimeoutGenerator.generate(self.BET_TIMEOUT)

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

            bet = player.bet(min_bet=min_bet, max_bet=max_bet, opening=opening, timeout=timeout)

            if bet == -1:
                if opening:
                    bet_type = "pass"
                else:
                    self._folder_keys.append(player_key)
                    bet_type = "fold"

            elif not bet:
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

        except (ChannelError, MessageFormatError, MessageTimeout) as e:
            self._add_faulty_player(player_key, e)

        self._logger.info("{}: {} bet: {} ({})".format(self, player, bet, bet_type))
        self.broadcast({
            "event": "bet",
            "bet": bet,
            "bet_type": bet_type,
            "player": player_key})

        return bet, bet_type

    def dto(self):
        game_dto = {
            "game": self._id,
            "pot": self._pot,
            "dealer": self._dealer_key,
            "players": []}

        for player_key, player in enumerate(self._players):
            with_score = player_key in self._public_cards_keys
            player_dto = player.dto(with_score=with_score)
            player_dto.update({
                "alive": player_key not in self._folder_keys,
                "bet": self._bets[player_key],
            })
            game_dto["players"].append(player_dto)

        return game_dto

    def broadcast(self, message={}):
        self._logger.debug("{}: broadcast {}".format(self, message))
        """Sends a game-update message to every player"""
        message.update(self.dto())
        if "msg_id" not in message:
            message["msg_id"] = "game-update"
        for player in self._players:
            player.try_send_message(message)


class TimeoutGenerator:
    @staticmethod
    def generate(seconds):
        return time.time() + seconds + 2  # Added a couple of extra seconds to deal with network overhead
