from poker import GameSubscriber


class MongoGameSubscriber(GameSubscriber):
    def __init__(self, mongodb):
        self._collection = mongodb.get_collection("games")

    def game_event(self, event, event_data):
        self._collection.insert(dict(event_data))
