from poker import Player


class PlayerConsole(Player):
    def __init__(self, name, money):
        self._name = name
        self._money = money
        self._cards = None
        self._score = None

    def get_name(self):
        """Player name"""
        return self._name

    def get_money(self):
        """Player money"""
        return self._money

    def set_money(self, money):
        """Sets player money"""
        self._money = money

    def get_cards(self):
        """Gets the list of cards assigned to the player"""
        return self._cards

    def get_score(self):
        """Gets the player score. Returns a Score object."""
        return self._score

    def set_cards(self, cards, score):
        """Assigns a list of cards to the player"""
        self._cards = cards
        self._score = score

    def discard_cards(self):
        """Gives players the opportunity to discard some of their cards.
        Returns a list of discarded cards."""
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
                    return remaining_cards, discards
                return self._cards, []
            except (ValueError, IndexError):
                print("One or more invalid card id.")

    def bet(self, min_bet=0.0, max_bet=0.0, opening=False):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        print(str(self))
        print(str(self._score))

        if max_bet == -1:
            input("Not allowed to open. Press enter to continue.")
            return -1

        while True:
            message = "Type your bet."
            if min_bet:
                message += " min bet: ${:,.2f}".format(min_bet)
            if max_bet:
                message += " max bet: ${:,.2f}".format(max_bet)
            message += " -1 to " + ("skip opening" if opening else "fold") + ": "

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
        """Sends a message to the client."""
        pass

    def recv_message(self):
        """Receives a message to the client."""
        pass

    def __str__(self):
        return "\n" + "{} ${:,.2f}".format(self.get_name(), self.get_money())
