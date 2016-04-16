    from . import Card
import logging


class GameError(Exception):
    pass


class HandFailException(Exception):
    pass


class Game:
    # Phases
    PHASE_CARDS_ASSIGNMENT = "cards-assignment"
    PHASE_OPENING_BET = "opening-bet"
    PHASE_CARDS_CHANGE = "cards-change"
    PHASE_FINAL_BET = "final-bet"
    PHASE_SHOW_CARDS = "show-cards"
    PHASE_WINNER_DESIGNATION = "winner-designation"

    def __init__(self, players, deck, score_detector, stake=10.0, logger=None):
        self._players = players
        self._deck = deck
        self._score_detector = score_detector
        self._stake = stake
        self._phase = None
        self._failed_hands = 0
        self._dealer_key = 0
        self._folder_keys = []
        self._pot = 0.0
        self._bets = [0.0] * len(players)
        # Pair of J, Q, K, A
        self._min_opening_scores = [score_detector.get_score([Card(r, 0), Card(r, 1)]) for r in [11, 12, 13, 14]]
        self._logger = logger if logger else logging

    def play_hand(self):
        """Play a single hand."""
        while True:
            try:
                # Initialization
                self._deck.initialize()
                self._folder_keys = [key for key, player in enumerate(self._players) if player.get_error()]

                if len(self._players) - len(self._folder_keys) < 2:
                    raise GameError("Not enough players to play another hand")

                # Cards assignment
                self._assign_cards()

                # Opening
                player_key = self._opening_bet_round()

                # 2 or more players alive
                if len(self._players) - len(self._folder_keys) > 1:
                    # Change cards
                    self._change_cards()
                    # Final bet round
                    player_key = self._final_bet_round(player_key)

                # 2 or more players still alive
                if len(self._players) - len(self._folder_keys) > 1:
                    # Show cards (winner detection)
                    player_key = self._show_cards(player_key)

                # Broadcast winner key
                self._phase = Game.PHASE_WINNER_DESIGNATION
                self._broadcast({"player": player_key})

                # Winner and hand finalization
                winner = self._players[player_key]
                winner.set_money(winner.get_money() + self._pot)
                self._logger.info("Player {} won".format(winner.get_id()))

                # Re-initialize pot, bets and move to the next dealer
                self._pot = 0.0
                self._bets = [0.0] * len(self._players)
                self._dealer_key = (self._dealer_key + 1) % len(self._players)
                break

            except HandFailException:
                # Automatically play another hand if the last has failed
                self._failed_hands += 1
                continue

    def get_players_in_error(self):
        """Returns the list of players in error."""
        return [player for player in self._players if player.get_error()]

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
            player.set_cards(cards, score)
        # Broadcasting
        self._broadcast()

    def _opening_bet_round(self):
        self._phase = Game.PHASE_OPENING_BET
        # Define the minimum score to open
        min_opening_score = self._min_opening_scores[self._failed_hands % len(self._min_opening_scores)]
        # Opening bet round
        for player_key, player in self._players_round(self._dealer_key):
            max_bet = -1 if player.get_score().cmp(min_opening_score) < 0 else self._pot
            bet = player.bet(min_bet=1.0, max_bet=max_bet, opening=True)
            if bet == -1:
                # Broadcasting
                self._logger.info("Player {} did not open".format(player.get_id()))
                self._broadcast({"player": player_key, "bet": -1, "bet_type": "PASS"})
            else:
                # Updating pots
                player.set_money(player.get_money() - bet)
                self._pot += bet
                self._bets[player_key] += bet
                # Broadcasting
                self._logger.info("Player {} opening bet: ${:,.2f}".format(player.get_id(), bet))
                self._broadcast({"player": player_key, "bet": bet, "bet_type": "RAISE"})
                # Completing the bet round
                return self._bet_round(player_key, opening_bet=bet)
        raise HandFailException

    def _change_cards(self):
        self._phase = Game.PHASE_CARDS_CHANGE
        # Change cards
        for player_key, player in self._players_round(self._dealer_key):
            _, discards = player.discard_cards()
            if discards:
                new_cards = self._deck.get_cards(len(discards))
                self._deck.add_discards(discards)
                cards = [card for card in player.get_cards() if card not in discards] + new_cards
                score = self._score_detector.get_score(cards)
                player.set_cards(cards, score)
            # Broadcasting
            self._logger.info("Player {} changed {} cards".format(player.get_id(), len(discards)))
            self._broadcast({"player": player_key, "num_cards": len(discards)})

    def _final_bet_round(self, best_player_key):
        self._phase = Game.PHASE_FINAL_BET
        return self._bet_round(best_player_key)

    def _show_cards(self, best_player_key):
        self._phase = Game.PHASE_SHOW_CARDS
        # Works out the winner
        winner = None
        winner_key = -1
        for player_key, player in self._players_round(best_player_key):
            if not winner or player.get_score().cmp(winner.get_score()) > 0:
                winner = player
                winner_key = player_key
                self._logger.info("Player {} score:\n{}".format(player.get_id(), str(player.get_score())))
                self._broadcast({
                    "player": player_key,
                    "score": {
                        "category": player.get_score().get_category(),
                        "cards": [(c.get_rank(), c.get_suit()) for c in player.get_score().get_cards()]}})
            else:
                self._logger.info("Player {} fold.".format(player.get_id()))
                self._broadcast({"player": player_key, "score": None})

        return winner_key

    def _broadcast(self, message={}):
        """Sends a game-update message to every player"""
        message.update({
            "msg_id": "game-update",
            "players": [
                {
                    "id": player.get_id(),
                    "name": player.get_name(),
                    "money": player.get_money(),
                    "alive": player_key not in self._folder_keys,
                    "bet": self._bets[player_key],
                    "dealer": player_key == self._dealer_key
                }
                for player_key, player in enumerate(self._players)
            ],
            "phase": self._phase,
            "pot": self._pot,
        })
        for player in self._players:
            player.try_send_message(message)

    def _players_round(self, start_id=0):
        """Iterate through a list of players who did not fold."""
        for i in range(len(self._players)):
            player_key = (i + start_id) % len(self._players)
            if player_key not in self._folder_keys:
                yield player_key, self._players[player_key]
        raise StopIteration

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
                player = self._players[player_key]

                # Only one player left, break and do not ask for a bet
                if len(self._players) - len(self._folder_keys) == 1:
                    best_player_key = player_key
                    break

                # Two or more players still alive
                # Works out the minimum bet for the current player
                min_partial_bet = 0.0 if best_player_key == -1 else bets[best_player_key] - bets[player_key]

                # Bet
                current_bet = player.bet(min_bet=min_partial_bet, max_bet=self._pot)

                bet_type = None

                if current_bet == -1:
                    # Fold
                    self._folder_keys.append(player_key)
                    bet_type = "FOLD"
                else:
                    player.set_money(player.get_money() - current_bet)
                    self._pot += current_bet

                    bets[player_key] += current_bet
                    if current_bet > min_partial_bet or best_player_key == -1:
                        # Raise
                        best_player_key = player_key

                    if current_bet > min_partial_bet:
                        # Raise
                        bet_type = "RAISE"
                    elif not current_bet:
                        # Check
                        bet_type = "CHECK"
                    else:
                        # Call
                        bet_type = "CALL"
                # Broadcasting
                self._logger.info("Player {}: {}".format(player.get_id(), bet_type))
                self._broadcast({"player": player_key, "bet": current_bet, "bet_type": bet_type})

            # Next player
            player_key = (player_key + 1) % len(self._players)

        return best_player_key
