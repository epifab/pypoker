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

    def get_cards(self, limit=5):
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
        cards1 = self.get_cards()
        cards2 = other.get_cards()

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

    def change_cards(self, given_up_cards):
        new_cards = self.get_cards(len(given_up_cards))
        self._discards += given_up_cards
        return new_cards


class Player:
    def get_name(self):
        raise NotImplementedError()

    def get_money(self):
        raise NotImplementedError()

    def add_money(self):
        raise NotImplementedError()

    def assign_cards(self, cards):
        raise NotImplementedError()

    def change_cards(self, deck):
        raise NotImplementedError()

    def get_score(self):
        raise NotImplementedError()

    def bet(self, min_bet=0.0, max_bet=0.0, check_allowed=True):
        raise NotImplementedError()


class ConsolePlayer(Player):
    def __init__(self, name, money, score_detector):
        self._name = name
        self._money = money
        self._score_detector = score_detector
        self._score = None

    def get_name(self):
        return self._name

    def get_money(self):
        return self._money

    def add_money(self, money):
        self._money += money

    def get_score(self):
        return self._score

    def assign_cards(self, cards):
        self._score = self._score_detector.get_score(cards)

    def __str__(self):
        return "\n" + "{} ${:,.2f}".format(self.get_name(), self.get_money()) + "\n" + str(self._score)

    def change_cards(self, deck):
        print(str(self))
        while True:
            try:
                cards = self._score.get_cards()
                given_up_card_ids = input("Please type a comma separated list of card id you wish to change (1 to 5, left to right): ")
                if given_up_card_ids:
                    # Convert the string into a list of unique integers
                    given_up_card_ids = set([int(card_id.strip()) - 1 for card_id in given_up_card_ids.split(",")])
                    # Works out the new card set
                    given_up_cards = [cards[card_id] for card_id in given_up_card_ids]
                    remaining_cards = [cards[card_id] for card_id in range(len(cards)) if
                                       card_id not in given_up_card_ids]
                    new_cards = deck.change_cards(given_up_cards)
                    self._score = self._score_detector.get_score(remaining_cards + new_cards)
                    print(str(self._score))
                    input()
                return
            except (ValueError, IndexError):
                print("One or more invalid card id.")

    def bet(self, min_bet=0.0, max_bet=0.0, check_allowed=True):
        print(str(self))
        while True:
            message = "Type your bet" if not min_bet else "${:,.2f} to call".format(min_bet)
            bet = input(message + " (-1 to fold): ".format(min_bet))
            try:
                bet = float(bet)
                if bet == -1:
                    print("Fold")
                    return -1
                elif bet < min_bet:
                    raise ValueError("Not enough money")
                elif not bet:
                    if check_allowed:
                        print("Check")
                    else:
                        print("Check not allowed.")
                        raise ValueError
                elif bet == min_bet:
                    print("Call")
                elif max_bet and bet > max_bet:
                    print("Max bet exceeded")
                    raise ValueError
                else:
                    print("Raise")
                self._money -= bet
                return bet
            except ValueError:
                print("Invalid bet.")


class Game:
    def __init__(self, players, deck, score_detector):
        self._players = players
        self._deck = deck
        self._score_detector = score_detector
        self._dealer_id = 0
        self._pot = 0.0
        self._folder_ids = []
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
        self._play_hand()
        while True:
            print()
            yes_no = input("Another hand? (Y/N) ")
            if yes_no == 'Y' or yes_no == 'y':
                self._play_hand()
                continue
            elif yes_no == 'N' or yes_no == 'n':
                break
            else:
                print("What?")

    def _player_ids(self, start_id=0):
        for i in range(len(self._players)):
            player_id = (i + start_id) % len(self._players)
            if player_id not in self._folder_ids:
                yield player_id
        raise StopIteration

    def _play_hand(self, failed_hands=0):
        # Initialization
        self._deck.initialize()
        self._folder_ids = []

        # Distribute cards
        for player_id in self._player_ids(self._dealer_id):
            self._players[player_id].assign_cards(self._deck.get_cards(5))

        min_opening_score = self._min_opening_scores[failed_hands % len(self._min_opening_scores)]

        # Opening bet round
        current_player_id = -1
        for player_id in self._player_ids(self._dealer_id):
            if self._players[player_id].get_score().cmp(min_opening_score) > 0:
                current_player_id = player_id
                break

        if current_player_id == -1:
            print("Nobody was able to open.")
            return

        # Opening bet round
        current_player_id = self._bet_round(current_player_id, check_allowed=False)

        # There are 2 or more players alive
        if len(self._folder_ids) + 1 < len(self._players):
            # Change cards
            for player_id in self._player_ids(self._dealer_id):
                self._players[player_id].change_cards(self._deck)
            # Final bet round
            self._bet_round(current_player_id, check_allowed=True)

        # Works out the winner
        winner_id = -1
        for player_id in self._player_ids(current_player_id):
            if winner_id == -1 or self._players[player_id].get_score().cmp(self._players[winner_id].get_score()) > 0:
                winner_id = player_id

        print("The winner is {}".format(self._players[winner_id].get_name()))
        self._players[winner_id].add_money(self._pot)
        self._pot = 0.0
        self._dealer_id = (self._dealer_id + 1) % len(self._players)

    def _bet_round(self, current_player_id, check_allowed=True):
        if len(self._players) == len(self._folder_ids):
            return -1
        bets = [0.0 for _ in self._players]
        highest_bet_player_id = -1
        while current_player_id != highest_bet_player_id:
            # Exclude folders
            if current_player_id not in self._folder_ids:
                # Only one player left
                if len(self._folder_ids) + 1 == len(self._players):
                    highest_bet_player_id = current_player_id
                    break
                # Two or more players still alive
                # Works out the minimum bet for the current player
                min_partial_bet = 0.0 if highest_bet_player_id == -1 \
                    else bets[highest_bet_player_id] - bets[current_player_id]
                check_allowed = check_allowed or highest_bet_player_id != -1
                # Bet
                current_bet = self._players[current_player_id].bet(min_partial_bet, self._pot, check_allowed)
                if current_bet == -1:
                    # Fold
                    self._folder_ids.append(current_player_id)
                else:
                    self._pot += current_bet
                    bets[current_player_id] += current_bet
                    if current_bet > min_partial_bet or highest_bet_player_id == -1:
                        # Raise
                        highest_bet_player_id = current_player_id
            # Next player
            current_player_id = (current_player_id + 1) % len(self._players)
        return highest_bet_player_id


score_detector = ScoreDetector(7)
deck = Deck(7)
players = [ConsolePlayer("Player 1", 1000, score_detector),
           ConsolePlayer("Player 2", 1000, score_detector),
           ConsolePlayer("Player 3", 1000, score_detector),
           ConsolePlayer("Player 4", 1000, score_detector)]
g = Game(players, deck, score_detector)
g.play_game()
