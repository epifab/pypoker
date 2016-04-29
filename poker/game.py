from poker import player
from . import Card, ChannelError, MessageTimeout, MessageFormatError
import logging
import random, string
import time


class GameError(Exception):
    pass


class HandFailException(Exception):
    pass


class Game:
    WAIT_AFTER_HAND = 10
    CHANGE_CARDS_TIMEOUT = 60
    BET_TIMEOUT = 60

    # Phases
    PHASE_NEW_GAME = "new-game"
    PHASE_CARDS_ASSIGNMENT = "cards-assignment"
    PHASE_OPENING_BET = "opening-bet"
    PHASE_CARDS_CHANGE = "cards-change"
    PHASE_FINAL_BET = "final-bet"
    PHASE_WINNER_DESIGNATION = "winner-designation"

    def __init__(self, players, deck, score_detector, stake=10.0, logger=None):
        self._id = ''.join(random.choice(string.ascii_lowercase) for i in range(5))
        self._players = players
        self._deck = deck
        self._score_detector = score_detector
        self._stake = stake
        self._phase = Game.PHASE_NEW_GAME
        self._failed_hands = 0
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
        self.broadcast({"event": "new-game"})
        while not self._players_in_error:
            try:
                self.play_hand()
            except GameError:
                break
        self.broadcast({"event": "game-over"})

    def play_hand(self):
        """Play a single hand."""
        while True:
            try:
                for player_key in self._players_in_error:
                    self.broadcast({"event": "player-left", "player": player_key})

                # Initialization
                self._deck.initialize()
                self._folder_keys = self._players_in_error
                self._public_cards_keys = []

                alive_player_keys = [k for (k, _) in enumerate(self._players) if k not in self._folder_keys]

                if len(alive_player_keys) == 0:
                    raise GameError("Every player left the table")

                elif len(alive_player_keys) > 1:
                    # Cards assignment
                    self._assign_cards()

                    # Opening
                    player_key = self._opening_bet_round()

                    # 2 or more players alive
                    if len(self._players) - len(self._folder_keys) > 1:
                        self._change_cards()
                        player_key = self._final_bet_round(player_key)

                    # 2 or more players still alive
                    if len(self._players) - len(self._folder_keys) > 1:
                        player_key = self._detect_winner(player_key)

                elif len(alive_player_keys) == 1:
                    player_key = alive_player_keys[0]

                self._phase = Game.PHASE_WINNER_DESIGNATION

                # Winner and hand finalization
                winner = self._players[player_key]
                winner.set_money(winner.get_money() + self._pot)

                # Re-initialize pot, bets and move to the next dealer
                self._pot = 0.0
                self._bets = [0.0] * len(self._players)
                self._dealer_key = (self._dealer_key + 1) % len(self._players)

                self._logger.info("{}: {} won".format(self, winner))
                self.broadcast({
                    "event": "winner-designation",
                    "player": player_key})

                time.sleep(Game.WAIT_AFTER_HAND)
                break

            except HandFailException:
                # Automatically play another hand if the last has failed
                self._failed_hands += 1
                continue

    def get_players(self):
        """Returns the list of players"""
        return self._players

    def _assign_cards(self):
        self._phase = Game.PHASE_CARDS_ASSIGNMENT
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
                self._players_in_error.append(player_key)

        self.broadcast({"event": "cards-assignment"})

    def _opening_bet_round(self):
        self._phase = Game.PHASE_OPENING_BET
        # Define the minimum score to open
        min_opening_score = self._min_opening_scores[self._failed_hands % len(self._min_opening_scores)]

        # Bet round
        for player_key, player in self._players_round(self._dealer_key):
            max_bet = -1 if player.get_score().cmp(min_opening_score) < 0 else self._pot

            # Ask remote player to bet
            bet, _ = self._bet(player_key=player_key, min_bet=1.0, max_bet=max_bet, opening=True)

            if bet != -1:
                return self._bet_round(player_key, opening_bet=bet)

        # Nobody opened
        raise HandFailException

    def _final_bet_round(self, best_player_key):
        self._phase = Game.PHASE_FINAL_BET
        return self._bet_round(best_player_key)

    def _bet_round(self, player_key, opening_bet=0.0):
        """Do a bet round. Returns the id of the player who made the strongest bet first.
        If opening_bet is specified, player_key is assumed to have made the opening bet already."""

        # Should never happen...
        if len(self._players) == len(self._folder_keys):
            return -1

        bets = [0.0] * len(self._players)
        best_player_key = -1

        if opening_bet:
            # player_key has already made an opening bet
            bets[player_key] = opening_bet
            best_player_key = player_key
            player_key = (player_key + 1) % len(self._players)

        while player_key != best_player_key:
            # Exclude folders
            if player_key not in self._folder_keys:
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

                if current_bet > min_partial_bet or best_player_key == -1:
                    best_player_key = player_key

            # Next player
            player_key = (player_key + 1) % len(self._players)

        return best_player_key

    def _players_round(self, start_id=0):
        """Iterate through a list of players who did not fold."""
        for i in range(len(self._players)):
            player_key = (i + start_id) % len(self._players)
            if player_key not in self._folder_keys:
                yield player_key, self._players[player_key]
        raise StopIteration

    def _change_cards(self):
        self._phase = Game.PHASE_CARDS_CHANGE
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

            except ChannelError as e:
                self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
                self._players_in_error.append(player_key)

            except MessageFormatError as e:
                self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
                player.try_send_message({"msg_id": "error", "error": e.args[0]})
                self._players_in_error.append(player_key)

            except MessageTimeout as e:
                self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
                player.try_send_message({"msg_id": "timeout"})

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
                # In a real poker italian game this player is not obligated to show his score
                pass
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

            if not bet:
                bet_type = "check"
            elif bet == min_bet:
                bet_type = "open" if opening else "call"
            elif bet > min_bet:
                bet_type = "raise"

            if bet > 0:
                player.set_money(player.get_money() - bet)
                self._pot += bet
                self._bets[player_key] += bet

        except ChannelError as e:
            self._logger.info("{}: {} error: {}".format(self, player, e.args[0]))
            self._players_in_error.append(player_key)

        except MessageFormatError as e:
            self._logger.info("{} {} error: {}".format(self, player, e.args[0]))
            player.try_send_message({"msg_id": "error", "error": e.args[0]})
            self._players_in_error.append(player_key)

        except MessageTimeout as e:
            self._logger.info("{}: {} timed out".format(self, player))
            player.try_send_message({"msg_id": "timeout"})

        if bet_type == "fold":
            self._folder_keys.append(player_key)

        self._logger.info("{}: {} bet: {} ({})".format(self, player, bet, bet_type))
        self.broadcast({
            "event": "bet",
            "bet": bet,
            "bet_type": bet_type,
            "player": player_key})

        return bet, bet_type

    def dto(self):
        game_dto = {
            "id": self._id,
            "phase": self._phase,
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
        return time.time() + seconds
