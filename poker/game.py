from . import Card, ChannelError, MessageTimeout, MessageFormatError
import gevent
import logging
import uuid


class GameError(Exception):
    pass


class WinnerDetection(Exception):
    pass


class GameFactory:
    def create_game(self, players, dealer_id):
        raise NotImplemented


class Game:
    WAIT_AFTER_HAND = 6
    WAIT_AFTER_CARDS_ASSIGNMENT = 1
    WAIT_AFTER_OPENING_BET = 0
    WAIT_AFTER_CARDS_CHANGE = 0
    WAIT_AFTER_FINAL_BET = 2

    CHANGE_CARDS_TIMEOUT = 45
    BET_TIMEOUT = 45
    TIMEOUT_TOLERANCE = 2

    class Event:
        NEW_GAME = "new-game"
        GAME_OVER = "game-over"
        CARDS_ASSIGNMENT = "cards-assignment"
        PLAYER_ACTION = "player-action"
        DEAD_PLAYER = "dead-player"
        BET = "bet"
        # @todo: cards change and dead hand only make sense in a traditional poker game
        CARDS_CHANGE = "cards-change"
        DEAD_HAND = "dead-hand"
        WINNER_DESIGNATION = "winner-designation"

    class EventListener:
        def game_event(self, event, event_data, game_data):
            raise NotImplemented

    def __init__(self, players, dealer_id=None, logger=None):
        self._id = str(uuid.uuid4())
        self._logger = logger if logger else logging
        # Dictionary of players keyed by their ids
        self._players = {player.get_id(): player for player in players}
        # List of player ids sorted according to the original players list
        self._player_ids = [player.get_id() for player in players]
        # Current dealer
        self._dealer_id = dealer_id if dealer_id else self._player_ids[0]
        # Players who fold
        self._folder_ids = set()
        # Players who timed out or died
        self._dead_player_ids = set()
        # Game event subscribers
        self._event_subscribers = set()

    def __str__(self):
        return "game {}".format(self._id)

    def subscribe(self, subscriber):
        self._event_subscribers.add(subscriber)

    def unsubscribe(self, subscriber):
        self._event_subscribers.remove(subscriber)

    def play_game(self):
        self._raise_event(Game.Event.NEW_GAME)
        try:
            self.play_hand()
        finally:
            self._raise_event(Game.Event.GAME_OVER)

    def play_hand(self):
        raise NotImplemented

    def dto(self):
        raise NotImplemented

    def send_player_cards(self, player):
        raise NotImplemented

    def _add_dead_player(self, player_id, exception):
        player = self._players[player_id]
        self._logger.info("{}: {} error: {}".format(self, player, exception.args[0]))
        player.try_send_message({"message_type": "error", "error": exception.args[0]})
        self._dead_player_ids.add(player_id)
        self._raise_event(Game.Event.DEAD_PLAYER, {"player_id": player_id})
        self._add_folder(player_id)

    def _add_folder(self, player_id):
        self._folder_ids.add(player_id)
        self._check_active_players()

    def _check_active_players(self):
        active_player_ids = [player_id for player_id in self._player_ids if player_id not in self._folder_ids]
        if len(active_player_ids) == 0:
            raise GameError("No active players")
        elif len(active_player_ids) == 1:
            raise WinnerDetection(active_player_ids[0])

    def _active_players_round(self, start_player_id):
        start_item = self._player_ids.index(start_player_id)

        for i in range(len(self._player_ids)):
            next_item = (i + start_item) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                yield player_id, self._players[player_id]
        raise StopIteration

    def _next_active_player_id(self, player_id):
        try:
            players = self._active_players_round(player_id)
            players.next()
            player_id, _ = players.next()
            return player_id
        except StopIteration:
            return player_id

    def _get_player_bet(self, player, min_bet=0.0, max_bet=0.0, timeout_epoch=None):
        """Bet handling.
        Returns the player bet. -1 to fold (or to skip the bet round during the opening phase)."""
        message = player.recv_message(timeout_epoch=timeout_epoch)
        if "message_type" not in message:
            raise MessageFormatError(attribute="message_type", desc="Attribute missing")

        MessageFormatError.validate_message_type(message, "bet")

        # No bet actually required (opening phase, score is too weak)
        if max_bet == -1:
            return -1

        if "bet" not in message:
            raise MessageFormatError(attribute="bet", desc="Attribute is missing")

        try:
            bet = float(message["bet"])

            # Fold
            if bet == -1.0:
                return bet

            # Bet range
            if bet < min_bet or bet > max_bet:
                raise MessageFormatError(
                    attribute="bet",
                    desc="Bet out of range. min: {} max: {}, actual: {}".format(min_bet, max_bet, bet))

            return bet

        except ValueError:
            raise MessageFormatError(attribute="bet", desc="'{}' is not a number".format(message.bet))

    def _raise_event(self, event, event_data=None):
        """Broadcast game events"""
        event_data = event_data if event_data else {}
        event_data["event"] = event
        game_data = self.dto()
        gevent.joinall([
            gevent.spawn(subscriber.game_event, event, event_data, game_data)
            for subscriber in self._event_subscribers
        ])
