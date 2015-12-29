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
        3: chr(3), # "Hearts",
        2: chr(4), # "Diamonds",
        1: chr(5), # "Clubs",
        0: chr(6)} # "Spades"}

    def __init__(self, rank, suit):
        if rank not in Card.RANKS:
            raise ValueError("Invalid card rank")
        if suit not in Card.SUITS:
            raise ValueError("Invalid card suit")
        self._value = (rank << 2) + suit

    def get_rank(self):
        return self._value >> 2

    def get_suit(self):
        return self._value & 3

    def __int__(self):
        return self._value

    def __repr__(self):
        return str(Card.RANKS[self.get_rank()]) + " of " + Card.SUITS[self.get_suit()]


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


class Cards:
    def __init__(self, cards, lowest_rank):
        self._cards = sorted(cards, key=int, reverse=True)
        self._ranks = collections.defaultdict(list)
        self._suits = collections.defaultdict(list)
        for card in self._cards:
            self._ranks[card.get_rank()].append(card)
            self._suits[card.get_suit()].append(card)
        self._unpaired = sorted([rank for (rank, cards) in self._ranks.items() if len(cards) == 1], reverse=True)
        self._pairs = sorted([rank for (rank, cards) in self._ranks.items() if len(cards) == 2], reverse=True)
        self._three_oak = sorted([rank for (rank, cards) in self._ranks.items() if len(cards) == 3], reverse=True)
        self._four_oak = sorted([rank for (rank, cards) in self._ranks.items() if len(cards) == 4], reverse=True)
        self._straight = Cards._get_straight(self._cards, lowest_rank)
        self._flush = Cards._get_flush(self._cards)
        self._straight_flush = Cards._get_straight_flush(self._cards, lowest_rank)
        self._sort_cards()

    def _sort_cards(self):
        score = self.get_score()
        best_sequence = []
        if score == Score.STRAIGHT_FLUSH:
            best_sequence = self.get_straight_flush()
        elif score == Score.FOUR_OF_A_KIND:
            best_sequence = self._ranks[self.get_four_oak_rank()]
        elif score == Score.FLUSH:
            best_sequence = self.get_flush()
        elif score == Score.FULL_HOUSE:
            best_sequence = self._ranks[self.get_three_oak_rank()] + self._ranks[self.get_pair1_rank()]
        elif score == Score.STRAIGHT:
            best_sequence = self.get_straight()
        elif score == Score.THREE_OF_A_KIND:
            best_sequence = self._ranks[self.get_three_oak_rank()]
        elif score == Score.DOUBLE_PAIR:
            best_sequence = self._ranks[self.get_pair1_rank()] + self._ranks[self.get_pair2_rank()]
        elif score == Score.PAIR:
            best_sequence = self._ranks[self.get_pair1_rank()]
        self._cards = best_sequence + [card for card in self._cards if card not in best_sequence]

    def get_card_list(self, best_five_only=False):
        return self._cards if not best_five_only or len(self._cards) < 5 else self._cards[0:5]

    def get_straight_flush(self):
        return self._straight_flush

    def get_flush(self):
        return self._flush

    def get_straight(self):
        return self._straight

    def get_unpaired(self):
        return self._unpaired

    def get_pair1_rank(self):
        return None if not self._pairs else self._pairs[0]

    def get_pair2_rank(self):
        return None if len(self._pairs) < 2 else self._pairs[1]

    def get_three_oak_rank(self):
        return None if not self._three_oak else self._three_oak[0]

    def get_four_oak_rank(self):
        return None if not self._four_oak else self._four_oak[0]

    def get_score(self):
        if self.get_straight_flush():
            return Score.STRAIGHT_FLUSH
        elif self.get_four_oak_rank():
            return Score.FOUR_OF_A_KIND
        elif self.get_flush():
            return Score.FLUSH
        elif self.get_three_oak_rank() and self.get_pair1_rank():
            return Score.FULL_HOUSE
        elif self.get_straight():
            return Score.STRAIGHT
        elif self.get_three_oak_rank():
            return Score.THREE_OF_A_KIND
        elif self.get_pair2_rank():
            return Score.DOUBLE_PAIR
        elif self.get_pair1_rank():
            return Score.PAIR
        else:
            return Score.HIGHEST_CARD

    def __str__(self):
        return ', '.join(self.get_card_list()) + '\n' + Score.CATEGORIES[self.get_score()]

    def _cmp(self, other):
        score_diff = self.get_score() - other.get_score()
        if score_diff:
            return score_diff
        cmp_methods = {
            Score.HIGHEST_CARD: self._cmp_highest_card,
            Score.PAIR: self._cmp_highest_card,
            Score.DOUBLE_PAIR: self._cmp_highest_card,
            Score.THREE_OF_A_KIND: self._cmp_highest_card,
            Score.STRAIGHT: self._cmp_highest_card,
            Score.FULL_HOUSE: self._cmp_highest_card,
            Score.FLUSH: self._cmp_highest_card,
            Score.FOUR_OF_A_KIND: self._cmp_highest_card,
            Score.STRAIGHT_FLUSH: self._cmp_straight_flush}
        return cmp_methods[self.get_score()](other)

    def _cmp_highest_card(self, other):
        return Cards._cmp_cards(self.get_card_list(best_five_only=True), other.get_card_list(best_five_only=True))

    def _cmp_straight_flush(self, other):
        # Min straight flush is stronger than royal flush
        if Cards._straight_is_max(self.get_straight_flush()) and Cards._straight_is_min(other.get_straight_flush()):
            return -1
        elif Cards._straight_is_min(self.get_straight_flush()) and Cards._straight_is_max(other.get_straight_flush()):
            return 1
        return self._cmp_cards(self.get_card_list(), other.get_card_list())

    def __lt__(self, other):
        return self._cmp(other) < 0

    def __eq__(self, other):
        return self._cmp(other) == 0

    def __str__(self):
        return str(self.get_card_list()) + "\n" + Score.CATEGORIES[self.get_score()]

    @staticmethod
    def _cmp_cards(cards1, cards2):
        rank_diff = Cards._cmp_ranks(cards1, cards2)
        if rank_diff != 0:
            return rank_diff
        return Cards._cmp_suits(cards1, cards2)

    @staticmethod
    def _cmp_ranks(cards1, cards2):
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
    def _get_straight(cards, lowest_rank):
        if len(cards) < 5:
            return None
        straight = [cards[0]]
        # The cards are assumed to be sorted by rank (in a descending order)
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
        suits = collections.defaultdict(list)
        for card in cards:
            suits[card.get_suit()].append(card)
            # Since cards is sorted by rank, as soon as a flush is recognized
            # we are sure it's the strongest flush of the set
            if len(suits[card.get_suit()]) == 5:
                return suits[card.get_suit()]
        return None

    @staticmethod
    def _get_straight_flush(cards, lowest_rank):
        suits = collections.defaultdict(list)
        for card in cards:
            suits[card.get_suit()].append(card)
            if len(suits[card.get_suit()]) >= 5:
                straight = Cards._get_straight(suits[card.get_suit()], lowest_rank)
                # Since cards is sorted by rank, as soon as a straight flush is recognized
                # we are sure it's the strongest flush of the set
                if straight:
                    return straight
        return None

    @staticmethod
    def _straight_is_min(straight_sequence):
        return straight_sequence[-1].get_rank() == 14

    @staticmethod
    def _straight_is_max(straight_sequence):
        return straight_sequence[0].get_rank() == 14

    def print_cards(self):
        lines = ["", "", "", "", "", "", ""]
        for card in self.get_card_list():
            lines[0] += "+-------+"
            lines[1] += "| {:<2}    |".format(Card.RANKS[card.get_rank()])
            lines[2] += "|       |"
            lines[3] += "|   {}   |".format(Card.SUITS[card.get_suit()])
            lines[4] += "|       |"
            lines[5] += "|    {:>2} |".format(Card.RANKS[card.get_rank()])
            lines[6] += "+-------+"
        print("\n".join(lines))
        print(Score.CATEGORIES[self.get_score()])


class CardsFactory:
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank

    def get_cards(self, cards):
        return Cards(cards, self._lowest_rank)


class Deck:
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank
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


class DeckFactory:
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank

    def get_deck(self):
        return Deck(self._lowest_rank)


class Player:
    def __init__(self, name, money, cards_factory):
        self.name = name
        self.money = money
        self._cards_factory = cards_factory
        self._cards = None

    def get_cards(self):
        return self._cards

    def assign_cards(self, cards):
        self._cards = self._cards_factory.get_cards(cards)

    def _print_cards(self):
        print()
        print("{} ${:,.2f}".format(self.name, self.money))
        self._cards.print_cards()

    def change_cards(self, deck):
        self._print_cards()
        while True:
            try:
                cards = self._cards.get_card_list()
                given_up_card_ids = input("Please type a comma separated list of card id you wish to change (1 to 5, left to right): ")
                if given_up_card_ids:
                    # Convert the string into a list of unique integers
                    given_up_card_ids = set([int(card_id.strip()) - 1 for card_id in given_up_card_ids.split(",")])
                    # Works out the new card set
                    given_up_cards = [cards[card_id] for card_id in given_up_card_ids]
                    remaining_cards = [cards[card_id] for card_id in range(len(cards)) if
                                       card_id not in given_up_card_ids]
                    new_cards = deck.change_cards(given_up_cards)
                    self._cards = self._cards_factory.get_cards(remaining_cards + new_cards)
                    Cards.print_cards(self._cards)
                    input()
                return
            except (ValueError, IndexError):
                print("One or more invalid card id.")

    def bet(self, min_bet=0.0, check_allowed=True):
        self._print_cards()
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
                else:
                    print("Raise")
                self.money -= bet
                return bet
            except ValueError:
                print("Invalid bet.")


class Game:
    def __init__(self, deck_factory, players):
        self._deck_factory = deck_factory
        self._deck = None
        self._players = players
        self._dealer_id = 0
        self._pot = 0.0
        self._folder_ids = []

    def play_game(self):
        self.play_hand()
        while True:
            print()
            yes_no = input("Another hand? (Y/N) ")
            if yes_no == 'Y' or yes_no == 'y':
                self.play_hand()
                continue
            elif yes_no == 'N' or yes_no == 'n':
                break
            else:
                print("What?")

    def player_ids(self, start_id=0):
        for i in range(len(self._players)):
            player_id = (i + start_id) % len(self._players)
            if player_id not in self._folder_ids:
                yield player_id
        raise StopIteration

    def play_hand(self):
        # Initialization
        self._pot = 0.0
        self._deck = self._deck_factory.get_deck()
        self._folder_ids = []

        # Distribute cards
        for player_id in self.player_ids(self._dealer_id):
            self._players[player_id].assign_cards(self._deck.get_cards(5))

        # Opening
        current_player_id = -1
        for player_id in self.player_ids(self._dealer_id):
            cards = self._players[player_id].get_cards()
            if cards.get_score() > Score.PAIR or cards.get_score() == Score.PAIR and cards.get_pair1_rank() >= 11:
                current_player_id = player_id
                break

        if current_player_id == -1:
            print("Nobody was able to open.")
            return

        current_player_id = self.bet_round(current_player_id, check_allowed=False)

        # Change cards
        for player_id in self.player_ids(self._dealer_id):
            self._players[player_id].change_cards(self._deck)

        # Final bet
        self.bet_round(current_player_id, check_allowed=True)

        # Works out the winner
        winner_id = -1
        for player_id in self.player_ids(current_player_id):
            if winner_id == -1 or self._players[player_id].get_cards() > self._players[winner_id].get_cards():
                winner_id = player_id

        print("The winner is {}".format(self._players[winner_id].name))
        self._players[winner_id].money += self._pot
        self._dealer_id = (self._dealer_id + 1) % len(self._players)

    def bet_round(self, current_player_id, check_allowed=True):
        bets = [0.0 for _ in self._players]
        highest_bet_player_id = -1
        while current_player_id != highest_bet_player_id:
            # Exclude folders
            if current_player_id not in self._folder_ids:
                # Works out the minimum bet
                min_partial_bet = 0.0 if highest_bet_player_id == -1 \
                    else bets[highest_bet_player_id] - bets[current_player_id]
                # Bet
                check_allowed = check_allowed or highest_bet_player_id != -1
                current_bet = self._players[current_player_id].bet(min_partial_bet, check_allowed)
                if current_bet == -1:
                    # Fold
                    self._folder_ids.append(current_player_id)
                else:
                    self._pot += current_bet
                    bets[current_player_id] += current_bet
                    if current_bet > min_partial_bet:
                        # Raise
                        highest_bet_player_id = current_player_id
            # Next player
            current_player_id = (current_player_id + 1) % len(self._players)
        return highest_bet_player_id


deck_factory = DeckFactory(7)
cards_factory = CardsFactory(7)
players = [Player("Player 1", 1000, cards_factory),
           Player("Player 2", 1000, cards_factory),
           Player("Player 3", 1000, cards_factory),
           Player("Player 4", 1000, cards_factory)]
g = Game(deck_factory, players)
g.play_game()
