from poker import Player, Card, MessageException


class PlayerConsole(Player):
    def __init__(self, id, name, money):
        Player.__init__(self, id, name, money)

    def discard_cards(self):
        """Gives players the opportunity to discard some of their cards.
        Returns a tuple: (remaining cards, discards)."""
        print(str(self))
        print(Card.format_cards(self._cards))
        while True:
            try:
                discard_keys = input("Please type a comma separated list of card (1 to 5 from left to right): ")
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


class PlayerClientConsole(PlayerConsole):
    def __init__(self, server, name, money):
        PlayerConsole.__init__(self, id=None, name=name, money=money)
        self._server = server
        self._connect()

    def _connect(self):
        self.send_message({
            'msg_id': 'connect',
            'player': {
                'id': self.get_id(),
                'name': self.get_name(),
                'money': self.get_money()}})

        message = self.recv_message()

        MessageException.validate_msg_id(message, "connect")

        try:
            self._id = message['player']['id']
        except IndexError:
            raise MessageException(attribute="player", desc="Missing required information")

    def set_cards(self, cards, score):
        """Assigns a list of cards to the player"""
        super().set_cards(cards, score)
        print(str(self))
        print(str(self._score))

    def discard_cards(self):
        """Gives players the opportunity to discard some of their cards.
        Returns a list of discarded cards."""
        remaining_cards, discards = super().discard_cards()
        discard_keys = [key for key in range(len(self._cards)) if self._cards[key] in discards]
        self.send_message({'msg_id': 'discard-cards', 'cards': discard_keys})
        return remaining_cards, discards

    def bet(self, min_bet=0.0, max_bet=0.0, opening=False):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        bet = super().bet(min_bet, max_bet, opening)
        self.send_message({'msg_id': 'bet', 'bet': bet})
        return bet

    def send_message(self, message):
        return self._server.send_message(message)

    def recv_message(self):
        return self._server.recv_message()

    def __str__(self):
        return "\n" + "{} ${:,.2f}".format(self.get_name(), self.get_money())
