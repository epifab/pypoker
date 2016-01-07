import random
import collections


class Card:
    RANKS = {
        2: "2",
        3: "3",
        4: "4",
        5: "5",
        6: "6",
        7: "7",
        8: "8",
        9: "9",
        10: "10",
        11: "J",
        12: "Q",
        13: "K",
        14: "A"}
    SUITS = {
        3: chr(3),  # Hearts
        2: chr(4),  # Diamonds
        1: chr(5),  # Clubs
        0: chr(6)}  # Spades

    def __init__(self, rank, suit):
        if rank not in Card.RANKS:
            raise ValueError("Invalid card rank")
        if suit not in Card.SUITS:
            raise ValueError("Invalid card suit")
        self._value = (rank << 2) + suit

    def get_rank(self):
        """Card rank"""
        return self._value >> 2

    def get_suit(self):
        """Card suit"""
        return self._value & 3

    def __lt__(self, other):
        return int(self) < int(other)

    def __eq__(self, other):
        return int(self) == int(other)

    def __repr__(self):
        return str(Card.RANKS[self.get_rank()]) + " of " + Card.SUITS[self.get_suit()]

    def __int__(self):
        return self._value


class Score:
    HIGHEST_CARD = 0
    PAIR = 1
    DOUBLE_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FULL_HOUSE = 5
    FLUSH = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    CATEGORIES = {
        0: "Highest Card",
        1: "Pair",
        2: "Double Pair",
        3: "Three of a Kind",
        4: "Straight",
        5: "Full House",
        6: "Flush",
        7: "Four of a Kind",
        8: "Straight Flush"}

    def __init__(self, score, cards):
        self._score = score
        self._cards = cards

    def get_score(self):
        """Gets the highest score for the given list of cards."""
        return self._score

    def get_cards(self, limit=0):
        """Gets the list of cards sorted in a descending order according to their score."""
        return self._cards if not limit or len(self._cards) < limit else self._cards[0:limit]

    def cmp(self, other):
        """Compare scores.
        Returns a positive integer if self is lower than score2,
        0 if the two scores are identical, a negative integer if score2 is higher than this score."""

        # Compare scores first
        score_diff = self.get_score() - other.get_score()
        if score_diff:
            return score_diff

        # Same score, compare the list of cards
        cards1 = self.get_cards(limit=5)
        cards2 = other.get_cards(limit=5)

        # In the traditional italian poker royal flushes are weaker than minimum straight flushes (e.g. 10, 9, 8, 7, A)
        # This is done so you are not mathematically sure to have the strongest hand.
        if self.get_score() == Score.STRAIGHT_FLUSH:
            if Score._straight_is_max(cards1) and Score._straight_is_min(cards2):
                return -1
            elif Score._straight_is_min(cards1) and Score._straight_is_max(cards2):
                return 1

        return Score._cmp_cards(cards1, cards2)

    @staticmethod
    def _cmp_cards(cards1, cards2):
        """Compare two list of cards according to ranks and suits."""
        rank_diff = Score._cmp_ranks(cards1, cards2)
        if rank_diff:
            return rank_diff
        return Score._cmp_suits(cards1, cards2)

    @staticmethod
    def _cmp_ranks(cards1, cards2):
        """Compare two list of cards ranks.
        Returns a negative integer if cards1 < cards2, positive if cards1 > cards2 or 0 if their ranks are identical"""
        for i in range(len(cards1)):
            try:
                rank_diff = cards1[i].get_rank() - cards2[i].get_rank()
                if rank_diff:
                    return rank_diff
            except IndexError:
                # cards1 is longer than cards2
                return 1
        return 0 if len(cards1) == len(cards2) else -1 # cards2 is longer than cards1

    @staticmethod
    def _cmp_suits(cards1, cards2):
        """Compare two list of cards suits.
        Returns a negative integer if cards1 < cards2, positive if cards1 > cards2 or 0 if their suits are identical"""
        for i in range(len(cards1)):
            try:
                suit_diff = cards1[i].get_suit() - cards2[i].get_suit()
                if suit_diff:
                    return suit_diff
            except IndexError:
                # cards1 is longer than cards2
                return 1
        return 0 if len(cards1) == len(cards2) else -1 # cards2 is longer than cards1

    @staticmethod
    def _straight_is_min(straight_sequence):
        return straight_sequence[4].get_rank() == 14

    @staticmethod
    def _straight_is_max(straight_sequence):
        return straight_sequence[0].get_rank() == 14

    def __str__(self):
        lines = ["", "", "", "", "", "", ""]
        for card in self.get_cards():
            lines[0] += "+-------+"
            lines[1] += "| {:<2}    |".format(Card.RANKS[card.get_rank()])
            lines[2] += "|       |"
            lines[3] += "|   {}   |".format(Card.SUITS[card.get_suit()])
            lines[4] += "|       |"
            lines[5] += "|    {:>2} |".format(Card.RANKS[card.get_rank()])
            lines[6] += "+-------+"
        return "\n".join(lines) + "\n" + Score.CATEGORIES[self.get_score()]


class ScoreDetector:
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank

    def get_score(self, cards):
        score, cards = ScoreDetector._detect_score(cards, self._lowest_rank)
        return Score(score, cards)

    @staticmethod
    def _detect_score(cards, lowest_rank):
        """Detects the highest score in the list of cards.
        Returns a tuple (score, cards) where score is an integer (see Score class) and cards is a list of cards sorted
        according to the score in a descending order.
        For instance, the following list of cards in input: [10?, A?, J?, 10?, J?]
        will produce the following tuple: (Score.DOUBLE_PAIR, [J?, J?, 10?, 10?, A?]"""

        def merge_sequence(sequence1, sequence2): return sequence1 + [c for c in sequence2 if c not in sequence1]

        # Sort the list of cards in a descending order
        cards = sorted(cards, key=int, reverse=True)

        # Straight flush
        straight_flush = ScoreDetector._get_straight_flush(cards, lowest_rank)
        if straight_flush:
            return Score.STRAIGHT_FLUSH, merge_sequence(straight_flush, cards)

        # Makes a dictionary keyed by rank and valued by list of cards of the same rank
        ranks = collections.defaultdict(list)
        for card in cards:
            ranks[card.get_rank()].append(card)

        # List of four of a kind ranks
        four_oak_rank = sorted([rank for (rank, cards) in ranks.items() if len(cards) == 4], reverse=True)

        # Four of a kind
        if four_oak_rank:
            return Score.FOUR_OF_A_KIND, merge_sequence(ranks[four_oak_rank[0]], cards)

        # Flush
        flush = ScoreDetector._get_flush(cards)
        if flush:
            return Score.FLUSH, flush

        # List of three of a kind and pair ranks
        three_oak_ranks = sorted([rank for (rank, cards) in ranks.items() if len(cards) == 3], reverse=True)
        pair_ranks = sorted([rank for (rank, cards) in ranks.items() if len(cards) == 2], reverse=True)

        # Full house
        if three_oak_ranks and pair_ranks:
            return Score.FULL_HOUSE, merge_sequence(ranks[three_oak_ranks[0]] + ranks[pair_ranks[0]], cards)

        # Straight
        straight = ScoreDetector._get_straight(cards, lowest_rank)
        if straight:
            return Score.STRAIGHT, merge_sequence(straight, cards)

        # Three of a kind
        if three_oak_ranks:
            return Score.THREE_OF_A_KIND, merge_sequence(ranks[three_oak_ranks[0]], cards)

        # Double pair
        if len(pair_ranks) > 1:
            return Score.DOUBLE_PAIR, merge_sequence(ranks[pair_ranks[0]] + ranks[pair_ranks[1]], cards)

        # Pair
        if pair_ranks:
            return Score.PAIR, merge_sequence(ranks[pair_ranks[0]], cards)

        return Score.HIGHEST_CARD, cards

    @staticmethod
    def _get_straight(cards, lowest_rank):
        """Detects and returns the highest straight from a list of cards sorted in a descending order."""
        if len(cards) < 5:
            return None

        straight = [cards[0]]

        for i in range(1, len(cards)):
            if cards[i].get_rank() == cards[i - 1].get_rank() - 1:
                straight.append(cards[i])
                if len(straight) == 5:
                    return straight
            elif cards[i].get_rank() != cards[i - 1].get_rank():
                straight = [cards[i]]

        # The Ace can go under the lowest rank card
        if len(straight) == 4 and cards[0].get_rank() == 14 and straight[-1].get_rank() == lowest_rank:
            straight.append(cards[0])
            return straight
        return None

    @staticmethod
    def _get_flush(cards):
        """Detect and returns the highest flush from a list of cards sorted in a descending order."""
        suits = collections.defaultdict(list)
        for card in cards:
            suits[card.get_suit()].append(card)
            # Since cards is sorted, the first flush detected is guaranteed to be the highest one
            if len(suits[card.get_suit()]) == 5:
                return suits[card.get_suit()]
        return None

    @staticmethod
    def _get_straight_flush(cards, lowest_rank):
        """Detect and returns the highest straight flush from a list of cards sorted by rank in a descending order."""
        suits = collections.defaultdict(list)
        for card in cards:
            suits[card.get_suit()].append(card)
            if len(suits[card.get_suit()]) >= 5:
                straight = ScoreDetector._get_straight(suits[card.get_suit()], lowest_rank)
                # Since cards is sorted, the first straight flush detected is guaranteed to be the highest one
                if straight:
                    return straight
        return None


class Deck:
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank
        self._cards = None
        self._discards = None

    def initialize(self):
        self._cards = [Card(rank, suit) for rank in range(self._lowest_rank, 15) for suit in range(0, 4)]
        self._discards = []
        random.shuffle(self._cards)

    def get_cards(self, num_cards=1):
        new_cards = []
        if len(self._cards) < num_cards:
            new_cards = self._cards
            self._cards = self._discards
            self._discards = []
            random.shuffle(self._cards)
        return new_cards + [self._cards.pop() for _ in range(num_cards - len(new_cards))]

    def change_cards(self, discards):
        new_cards = self.get_cards(len(discards))
        self._discards += discards
        return new_cards


class Player:
    def get_id(self):
        raise NotImplementedError

    def get_name(self):
        raise NotImplementedError

    def get_money(self):
        raise NotImplementedError

    def get_cards(self):
        raise NotImplementedError

    def set_money(self):
        raise NotImplementedError

    def set_cards(self, cards):
        raise NotImplementedError

    def discard_cards(self):
        raise NotImplementedError

    def get_score(self):
        raise NotImplementedError

    def bet(self, min_bet=0.0, max_bet=0.0, min_score=None):
        raise NotImplementedError

    def send_message(self, message):
        raise NotImplementedError


class ConsolePlayer(Player):
    def __init__(self, identifier, name, money, score_detector):
        self._id = identifier
        self._name = name
        self._money = money
        self._cards = None
        self._score_detector = score_detector
        self._score = None

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def get_money(self):
        return self._money

    def set_money(self, money):
        self._money = money

    def get_cards(self):
        return self._cards

    def set_cards(self, cards):
        self._cards = cards
        self._score = self._score_detector.get_score(cards)
        print(str(self))
        print(str(self._score))

    def discard_cards(self):
        print(str(self))
        while True:
            try:
                for k in range(len(self._cards)):
                    print("{}) {}".format(k + 1, str(self._cards[k])))
                discard_keys = input("Please type a comma separated list of card id you wish to change: ")
                if discard_keys:
                    # Convert the string into a list of unique integers
                    discard_keys = set([int(card_id.strip()) - 1 for card_id in discard_keys.split(",")])
                    if len(discard_keys) > 4:
                        print("You cannot change more than 4 cards")
                        continue
                    # Works out the new card set
                    discards = [self._cards[key] for key in discard_keys]
                    remaining_cards = [self._cards[key] for key in range(len(self._cards)) if key not in discard_keys]
                    self.set_cards(remaining_cards)
                    return discards
                return []
            except (ValueError, IndexError):
                print("One or more invalid card id.")

    def get_score(self):
        return self._score

    def bet(self, min_bet=0.0, max_bet=0.0, min_score=None):
        print(str(self))
        print(str(self._score))

        if min_score and self._score.cmp(min_score) < 0:
            input("Not allowed to open. Press enter to continue.")
            return -1

        while True:
            message = "Type your bet."
            if min_bet:
                message += " min bet: ${:,.2f}".format(min_bet)
            if max_bet:
                message += " max bet: ${:,.2f}".format(max_bet)
            message += " -1 to " + ("skip opening" if min_score else "fold") + ": "

            bet = input(message)

            try:
                bet = float(bet)
                if bet == -1:
                    return -1
                elif bet < min_bet:
                    raise ValueError
                elif max_bet and bet > max_bet:
                    raise ValueError
                self._money -= bet
                return bet
            except ValueError:
                print("Invalid bet.")

    def send_message(self, message):
        pass

    def __str__(self):
        return "\n" + "{} #{} ${:,.2f}".format(self.get_name(), self.get_id(), self.get_money())


class Game:
    # Phases
    PHASE_CARDS_ASSIGNMENT = 'CARDS_ASSIGNMENT'
    PHASE_OPENING = 'OPENING'
    PHASE_CARDS_CHANGE = 'CARDS_CHANGE'
    PHASE_FINAL_BET = 'FINAL_BET'
    PHASE_SHOW_CARDS = 'SHOW_CARDS'

    def __init__(self, players, deck, score_detector, stake=0.0):
        self._players = players
        self._deck = deck
        self._score_detector = score_detector
        self._stake = stake
        self._phase = None
        self._dealer_key = 0
        self._folder_keys = []
        self._pot = 0.0
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

    def play_hand(self, failed_hands=0):
        # Initialization
        self._deck.initialize()
        self._folder_keys = []

        ################################
        # Cards assignment phase
        ################################
        self._phase = Game.PHASE_CARDS_ASSIGNMENT

        for _, player in self._players_round(self._dealer_key):
            # Collect stakes
            player.set_money(player.get_money() - self._stake)
            self._pot += self._stake
            # Distribute cards
            player.set_cards(self._deck.get_cards(5))
            self._broadcast({'player_id': player.get_id()})

        ################################
        # Opening phase
        ################################
        self._phase = Game.PHASE_OPENING

        # Define the minimum score to open
        min_opening_score = self._min_opening_scores[failed_hands % len(self._min_opening_scores)]

        # Opening bet round
        opening_bet = None
        strongest_bet_player_key = -1
        for player_key, player in self._players_round(self._dealer_key):
            bet = player.bet(min_bet=1.0, max_bet=self._pot, min_score=min_opening_score)
            if bet == -1:
                print("Player '{}' did not open".format(player.get_name()))
                self._broadcast({'player_id': player.get_id(), 'bet': -1, 'bet_type': 'PASS'})
            else:
                print("Player '{}' opening bet: ${:,.2f}".format(player.get_name(), bet))
                self._broadcast({'player_id': player.get_id(), 'bet': bet, 'bet_type': 'RAISE'})
                opening_bet = bet
                strongest_bet_player_key = player_key
                self._pot += opening_bet
                break

        if not opening_bet:
            print("Nobody opened.")
            return

        # Opening bet round
        strongest_bet_player_key = self._bet_round(strongest_bet_player_key, opening_bet=opening_bet)

        num_active_players = len(self._players) - len(self._folder_keys)

        # There are 2 or more players alive
        if num_active_players > 1:
            ################################
            # Cards change phase
            ################################
            self._phase = Game.PHASE_CARDS_CHANGE

            # Change cards
            for _, player in self._players_round(self._dealer_key):
                discards = player.discard_cards()
                if discards:
                    remaining_cards = player.get_cards()
                    new_cards = self._deck.get_cards(len(discards))
                    player.set_cards(remaining_cards + new_cards)
                self._broadcast({'player_id': player.get_id(), 'num_cards': len(discards)})

            ################################
            # Final bet phase
            ################################
            self._phase = Game.PHASE_FINAL_BET

            # Final bet round
            strongest_bet_player_key = self._bet_round(strongest_bet_player_key)

        ################################
        # Show cards phase
        ################################
        self._phase = Game.PHASE_SHOW_CARDS

        # Works out the winner
        winner = None
        for _, player in self._players_round(strongest_bet_player_key):
            if not winner or player.get_score().cmp(winner.get_score()) > 0:
                winner = player
                if num_active_players > 1:
                    self._broadcast({'player_id': player.get_id(), 'score': player.get_score()})
            else:
                self._broadcast({'player_id': player.get_id(), 'score': None})

        print("The winner is {}".format(winner.get_name()))
        winner.set_money(winner.get_money() + self._pot)
        self._pot = 0.0
        self._dealer_key = (self._dealer_key + 1) % len(self._players)

    def _broadcast(self, message):
        message['phase'] = self._phase
        for player in self._players:
            player.send_message(message)

    def _players_round(self, start_id=0):
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

                print("Player '{}' #{}: {}".format(player.get_name(), player.get_id(), bet_type))
                self._broadcast({'player_id': player.get_id(), 'bet': current_bet, 'bet_type': bet_type})

            # Next player
            player_key = (player_key + 1) % len(self._players)

        return highest_bet_player_key


score_detector = ScoreDetector(7)
deck = Deck(7)
players = [ConsolePlayer(1, "Player 1", 1000, score_detector),
           ConsolePlayer(2, "Player 2", 1000, score_detector),
           ConsolePlayer(3, "Player 3", 1000, score_detector),
           ConsolePlayer(4, "Player 4", 1000, score_detector)]
g = Game(players, deck, score_detector, 10.0)
g.play_game()
