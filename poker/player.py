class Player:
    def __init__(self, id: str, name: str, money: float):
        self._id: str = id
        self._name: str = name
        self._money: float = money

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def money(self) -> float:
        return self._money

    def dto(self):
        return {
            "id": self.id,
            "name": self.name,
            "money": self.money
        }

    def take_money(self, money: float):
        if money > self._money:
            raise ValueError("Player does not have enough money")
        if money < 0.0:
            raise ValueError("Money has to be a positive amount")
        self._money -= money

    def add_money(self, money: float):
        if money <= 0.0:
            raise ValueError("Money has to be a positive amount")
        self._money += money

    def __str__(self):
        return "player {}".format(self._id)
