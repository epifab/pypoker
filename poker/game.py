from poker.card import Card


class FailHandException(Exception):
    pass


class Game:
    # Phases
    PHASE_CARDS_ASSIGNMENT = 'CARDS_ASSIGNMENT'
    PHASE_OPENING = 'OPENING'
    PHASE_CARDS_CHANGE = 'CARDS_CHANGE'
    PHASE_FINAL_BET = 'FINAL_BET'
    PHASE_SHOW_CARDS = 'SHOW_CARDS'
    PHASE_WINNER_DETECTION = 'WINNER_DETECTION'

    def __init__(self, players, deck, score_detector, stake=0.0):
        self._players = players
        self._deck = deck
        self._score_detector = score_detector
        self._stake = stake
        self._phase = None
        self._failed_hands = 0
        self._dealer_key = 0
        self._folder_keys = []
        self._pot = 0.0
        self._bets = [0.0 for _ in players]
        self._min_opening_scores = [
            # Pair of J
            score_detector.get_score([Card(11, 0), Card(11, 1)]),
            # Pair of Q
            score_detector.get_score([Card(12, 0), Card(12, 1)]),
            # Pair of K
            score_detector.get_score([Card(13, 0), Card(13, 1)]),
            # Pair of A
            score_detector.get_score([Card(14, 0), Card(14, 1)])]

    def play_game(self):
        """Play an indefinite number of hands."""
        self.play_hand()
        while True:
            print()
            yes_no = input("Another hand? (Y/N) ")
            if yes_no.upper() == 'Y':
                self.play_hand()
                continue
            elif yes_no.upper() == 'N':
                break
            else:
                print("Invalid answer")

    def play_hand(self):
        """Play a single hand."""

        # Initialization
        self._deck.initialize()
        self._folder_keys = []

        # Cards assignment
        self._assign_cards()

        try:
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
            self._phase = Game.PHASE_CARDS_CHANGE
            self._broadcast({'winner': player_key})

            # Winner and hand finalization
            winner = self._players[player_key]
            winner.set_money(winner.get_money() + self._pot)
            print("Player '{}' won".format(winner.get_name()))

            # Re-initialize pot, bets and move to the next dealer
            self._pot = 0.0
            self._bets = [0.0 for _ in self._players]
            self._dealer_key = (self._dealer_key + 1) % len(self._players)

        except FailHandException:
            self._failed_hands += 1
            return False

    def _assign_cards(self):
        self._phase = Game.PHASE_CARDS_ASSIGNMENT
        # Assign cards
        for player_key, player in self._players_round(self._dealer_key):
            # Collect stakes
            self._pot += self._stake
            self._bets[player_key] += self._stake
            player.set_money(player.get_money() - self._stake)
            # Distribute cards
            player.set_cards(self._deck.get_cards(5))
        # Broadcasting
        self._broadcast()

    def _opening_bet_round(self):
        self._phase = Game.PHASE_OPENING
        # Define the minimum score to open
        min_opening_score = self._min_opening_scores[self._failed_hands % len(self._min_opening_scores)]
        # Opening bet round
        for player_key, player in self._players_round(self._dealer_key):
            bet = player.bet(min_bet=1.0, max_bet=self._pot, min_score=min_opening_score)
            if bet == -1:
                # Broadcasting
                print("Player '{}' did not open".format(player.get_name()))
                self._broadcast({'player': player_key, 'bet': -1, 'bet_type': 'PASS'})
            else:
                # Updating pots
                self._pot += bet
                self._bets[player_key] += bet
                # Broadcasting
                print("Player '{}' opening bet: ${:,.2f}".format(player.get_name(), bet))
                self._broadcast({'player': player_key, 'bet': bet, 'bet_type': 'RAISE'})
                # Completing the bet round
                return self._bet_round(player_key, opening_bet=bet)
        raise FailHandException

    def _change_cards(self):
        self._phase = Game.PHASE_CARDS_CHANGE
        # Change cards
        for player_key, player in self._players_round(self._dealer_key):
            discards = player.discard_cards()
            if discards:
                remaining_cards = player.get_cards()
                new_cards = self._deck.get_cards(len(discards))
                self._deck.add_discards(discards)
                player.set_cards(remaining_cards + new_cards)
            # Broadcasting
            print("Player '{}' changed {} cards".format(player.get_name(), len(discards)))
            self._broadcast({'player': player_key, 'num_cards': len(discards)})

    def _final_bet_round(self, strongest_bet_player_key):
        self._phase = Game.PHASE_FINAL_BET
        return self._bet_round(strongest_bet_player_key)

    def _show_cards(self, strongest_bet_player_key):
        self._phase = Game.PHASE_SHOW_CARDS
        # Works out the winner
        winner = None
        winner_key = -1
        for player_key, player in self._players_round(strongest_bet_player_key):
            if not winner or player.get_score().cmp(winner.get_score()) > 0:
                winner = player
                winner_key = player_key
                print("Player '{}':\n{}".format(player.get_name(), str(player.get_score())))
                self._broadcast({
                    'player': player_key,
                    'score': {
                        'score': player.get_score().get_score(),
                        'cards': player.get_score().get_cards()
                    },
                })
            else:
                print("Player '{}' fold.".format(player.get_name()))
                self._broadcast({'player': player_key, 'score': None})

        return winner_key

    def _broadcast(self, message={}):
        """Sends a game-update message to every player"""
        message.update({
            'msg_id': 'game-update',
            'players': {key: {'id': self._players[key].get_id(),
                              'name': self._players[key].get_name(),
                              'money': self._players[key].get_money(),
                              'alive': key not in self._folder_keys,
                              'bet': self._bets[key],
                              'dealer': key == self._dealer_key}
                        for key in range(len(self._players))},
            'phase': self._phase,
            'pot': self._pot,
        })
        for player in self._players:
            player.send_message(message)

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

        bets = [0.0 for _ in self._players]
        highest_bet_player_key = -1

        if opening_bet:
            # player_key has already made an opening bet
            bets[player_key] = opening_bet
            highest_bet_player_key = player_key
            player_key = (player_key + 1) % len(self._players)

        while player_key != highest_bet_player_key:
            # Exclude folders
            if player_key not in self._folder_keys:
                player = self._players[player_key]

                # Only one player left
                if len(self._folder_keys) + 1 == len(self._players):
                    highest_bet_player_key = player_key
                    break

                # Two or more players still alive
                # Works out the minimum bet for the current player
                min_partial_bet = 0.0 if highest_bet_player_key == -1 \
                    else bets[highest_bet_player_key] - bets[player_key]

                # Bet
                current_bet = self._players[player_key].bet(min_bet=min_partial_bet, max_bet=self._pot)

                bet_type = None

                if current_bet == -1:
                    # Fold
                    self._folder_keys.append(player_key)
                    bet_type = 'FOLD'
                else:
                    self._pot += current_bet
                    bets[player_key] += current_bet
                    if current_bet > min_partial_bet or highest_bet_player_key == -1:
                        # Raise
                        highest_bet_player_key = player_key

                    if current_bet > min_partial_bet:
                        # Raise
                        bet_type = 'RAISE'
                    elif not current_bet:
                        # Check
                        bet_type = 'CHECK'
                    else:
                        # Call
                        bet_type = 'CALL'
                # Broadcasting
                print("Player '{}': {}".format(player.get_name(), bet_type))
                self._broadcast({'player': player_key, 'bet': current_bet, 'bet_type': bet_type})

            # Next player
            player_key = (player_key + 1) % len(self._players)

        return highest_bet_player_key
