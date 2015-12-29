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
        11: "Jack",
        12: "Queen",
        13: "King",
        14: "Ace"}
    SUITS = {
        3: "Hearts",
        2: "Diamonds",
        1: "Clubs",
        0: "Spades"}

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


class CardSet:
    def __init__(self, cards, lowest_rank=2):
        if len(cards) != 5:
            raise ValueError("Expected set of 5 cards, .")
        self._cards = sorted(cards, key=int, reverse=True)
        self._suits = collections.defaultdict(list)
        self._ranks = collections.defaultdict(list)
        for card in self._cards:
            self._suits[card.get_suit()].append(card)
            self._ranks[card.get_rank()].append(card)
        self._unpaired = [cards for cards in self._ranks if len(cards) == 1]
        self._pairs = [cards for cards in self._ranks if len(cards) == 2]
        self._three_oak = [cards for cards in self._ranks if len(cards) == 2]
        self._four_oak = [cards for cards in self._ranks if len(cards) == 4]
        self._unpaired = sorted([rank for rank in self._ranks if self._ranks[rank] == 1], reverse=True)
        self._pairs = sorted([rank for rank in self._ranks if self._ranks[rank] == 2], reverse=True)
        self._three_oak = [rank for rank in self._ranks if self._ranks[rank] == 3]
        self._four_oak = [rank for rank in self._ranks if self._ranks[rank] == 4]
        # ~~~~~~~~~~~~~~~~~~~
        # Straights detection
        # ~~~~~~~~~~~~~~~~~~~
        self._is_straight = True
        # Note: in a straight the Ace can either go after the King or before the lowest rank card
        straight_start = 2 if self._cards[0].get_rank() == 14 and self._cards[-1].get_rank() == lowest_rank else 1
        for i in range(straight_start, len(self._cards)):
            if self._cards[i].get_rank() != self._cards[i - 1].get_rank() - 1:
                self._is_straight = False
                break
        if self._is_straight and straight_start == 2:
            # Minimum straight detected: move the ace at the end of the sequence
            self._cards.append(self._cards[0])
            del self._cards[0]

    def get_cards(self):
        return self._cards

    def is_straight(self):
        return self._is_straight

    def straight_is_min(self):
        return self._is_straight and self._cards[-1] == 15

    def straight_is_max(self):
        return self._is_straight and self._cards[0] == 15

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

    def is_flush(self):
        return len(self._suits) == 1

    def get_score(self):
        if self.is_flush() and self.is_straight():
            return Score.STRAIGHT_FLUSH
        elif self.get_four_oak_rank():
            return Score.FOUR_OF_A_KIND
        elif self.is_flush():
            return Score.FLUSH
        elif self.get_three_oak_rank() and self.get_pair1_rank():
            return Score.FULL_HOUSE
        elif self.is_straight():
            return Score.STRAIGHT
        elif self.get_three_oak_rank():
            return Score.THREE_OF_A_KIND
        elif self.get_pair2_rank():
            return Score.DOUBLE_PAIR
        elif self.get_pair1_rank():
            return Score.PAIR
        else:
            return Score.HIGHEST_CARD

    def __lt__(self, other):
        return self._cmp(other) < 0

    def __eq__(self, other):
        return self._cmp(other) == 0

    def __str__(self):
        return str(self.get_cards()) + "\n" + Score.CATEGORIES[self.get_score()]

    @staticmethod
    def _cmp_cards_ranks(cards1, cards2):
        for i in range(len(cards1)):
            rank_diff = cards1[i].get_rank() - cards2[i].get_rank()
            if rank_diff:
                return rank_diff
        return 0

    @staticmethod
    def _cmp_cards_suits(cards1, cards2):
        for i in range(len(cards1)):
            suit_diff = cards1[i].get_suit() - cards2[i].get_suit()
            if suit_diff:
                return suit_diff
        return 0

    @staticmethod
    def _cmp_cards(cards1, cards2):
        rank_diff = CardSet._cmp_cards_ranks(cards1, cards2)
        if rank_diff != 0:
            return rank_diff
        return CardSet._cmp_cards_suits(cards1, cards2)

    def _cmp(self, other):
        score_diff = self.get_score() - other.get_score()
        if score_diff:
            return score_diff
        cmp_methods = {
            Score.HIGHEST_CARD: self._cmp_highest_card,
            Score.PAIR: self._cmp_pair,
            Score.DOUBLE_PAIR: self._cmp_double_pair,
            Score.THREE_OF_A_KIND: self._cmp_three_oak,
            Score.STRAIGHT: self._cmp_straight,
            Score.FULL_HOUSE: self._cmp_full_house,
            Score.FLUSH: self._cmp_flush,
            Score.FOUR_OF_A_KIND: self._cmp_four_oak,
            Score.STRAIGHT_FLUSH: self._cmp_straight_flush}
        return cmp_methods[self.get_score()](other)

    def _cmp_highest_card(self, other):
        return CardSet._cmp_cards(self.get_cards(), other.get_cards())

    def _cmp_pair(self, other):
        rank_diff = self.get_pair1_rank() - other.get_pair1_rank()
        if rank_diff:
            return rank_diff
        return CardSet._cmp_cards(self.get_unpaired(), other.get_unpaired())

    def _cmp_double_pair(self, other):
        rank_diff = self.get_pair1_rank() - other.get_pair1_rank()
        if rank_diff:
            return rank_diff
        rank_diff = self.get_pair2_rank() - other.get_pair2_rank()
        if rank_diff:
            return rank_diff
        return CardSet._cmp_cards(self.get_unpaired(), other.get_unpaired())

    def _cmp_three_oak(self, other):
        return self.get_three_oak_rank() - other.get_three_oak_rank()

    def _cmp_straight(self, other):
        return CardSet._cmp_cards([self.get_cards()[0]], [other.get_cards()[0]])

    def _cmp_full_house(self, other):
        return self._cmp_three_oak(other)

    def _cmp_flush(self, other):
        return self._cmp_highest_card(other)

    def _cmp_four_oak(self, other):
        return self.get_four_oak_rank() - other.get_four_oak_rank()

    def _cmp_straight_flush(self, other):
        # Min straight flush is stronger than royal flush
        if self.straight_is_max() and other.straight_is_min():
            return -1
        elif self.straight_is_min() and other.straight_is_max():
            return 1
        return self._cmp_straight(other)


class CardSetFactory:
    def __init__(self, lowest_rank=2):
        self._lowest_rank = lowest_rank

    def get_card_set(self, cards):
        return CardSet(cards, self._lowest_rank)


class Deck:
    def __init__(self, lowest_rank=2):
        self._lowest_rank = lowest_rank
        self._cards = None

    def reset(self):
        self._cards = collections.deque([Card(rank, suit) for rank in range(self._lowest_rank, 15) for suit in range(0, 4)])
        random.shuffle(self._cards)

    def get_cards(self, num_cards=1):
        return [self._cards.popleft() for _ in range(num_cards)]

    def change_cards(self, given_up_cards):
        for card in given_up_cards:
            self._cards.append(card)
        return self.get_cards(len(given_up_cards))


class Player:
    def __init__(self, name, money, card_set_factory):
        self.name = name
        self.money = money
        self._card_set_factory = card_set_factory
        self._card_set = None

    def get_card_set(self):
        return self._card_set

    def assign_cards(self, cards):
        self._card_set = self._card_set_factory.get_card_set(cards)

    def _print_cards(self):
        print()
        print("{} ${:,.2f}".format(self.name, self.money))
        for i in range(len(self._card_set.get_cards())):
            print(" - {}: {}".format(i, self._card_set.get_cards()[i]))
        print(Score.CATEGORIES[self._card_set.get_score()])

    def change_cards(self, deck):
        self._print_cards()
        while True:
            try:
                cards = self._card_set.get_cards()
                given_up_card_ids = input("Please type a comma separated list of card id you wish to change: ")
                if given_up_card_ids:
                    # Convert the string into a list of unique integers
                    given_up_card_ids = set([int(card_id.strip()) for card_id in given_up_card_ids.split(",")])
                    # Works out the new card set
                    given_up_cards = [cards[card_id] for card_id in given_up_card_ids]
                    remaining_cards = [cards[card_id] for card_id in range(len(cards)) if
                                       card_id not in given_up_card_ids]
                    new_cards = deck.change_cards(given_up_cards)
                    print("New cards: {}".format(new_cards))
                    self._card_set = self._card_set_factory.get_card_set(remaining_cards + new_cards)
                    print(self._card_set)
                    input("")
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
    def __init__(self, deck, players):
        self._deck = deck
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
        self._deck.reset()

        # Distribute cards
        for player_id in self.player_ids(self._dealer_id):
            self._players[player_id].assign_cards(self._deck.get_cards(5))

        # Opening
        current_player_id = -1
        for player_id in self.player_ids(self._dealer_id):
            card_set = self._players[player_id].get_card_set()
            if card_set.get_score() > Score.PAIR or card_set.get_score() == Score.PAIR and card_set.get_pair1_rank() >= 11:
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

        print("Working out who is the winner...")

        # Works out the winner
        winner_id = -1
        for player_id in self.player_ids(current_player_id):
            if winner_id == -1 or self._players[player_id].get_card_set() > self._players[winner_id].get_card_set():
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


d = Deck(7)
csf = CardSetFactory(7)
players = [Player("A", 1000, csf), Player("B", 1000, csf), Player("C", 1000, csf), Player("D", 1000, csf)]

g = Game(d, players)
g.play_game()
