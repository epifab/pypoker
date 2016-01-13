class Player:
    def get_name(self):
        raise NotImplementedError

    def get_money(self):
        raise NotImplementedError

    def set_money(self):
        raise NotImplementedError

    def get_cards(self):
        raise NotImplementedError

    def set_cards(self, cards):
        raise NotImplementedError

    def get_score(self):
        raise NotImplementedError

    def discard_cards(self):
        raise NotImplementedError

    def bet(self, min_bet=0.0, max_bet=0.0, opening=False):
        raise NotImplementedError

    def send_message(self, message):
        raise NotImplementedError

    def recv_message(self):
        raise NotImplementedError