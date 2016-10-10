from . import Card, ChannelError, MessageTimeout, MessageFormatError
import gevent
import logging
import uuid
import time


class GameError(Exception):
    pass


class EndGameException(Exception):
    pass


class GameFactory:
    def create_game(self, players, dealer_id):
        raise NotImplemented


class Game:
    WAIT_AFTER_CARDS_ASSIGNMENT = 1
    WAIT_AFTER_CARDS_CHANGE = 0
    WAIT_AFTER_BET = 0
    WAIT_AFTER_WINNER_DESIGNATION = 2
    WAIT_AFTER_HAND = 4

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
        CARDS_CHANGE = "cards-change"
        DEAD_HAND = "dead-hand"
        WINNER_DESIGNATION = "winner-designation"

    class EventListener:
        def game_event(self, event, event_data, game_data):
            raise NotImplemented

    def __init__(self, players, score_detector, dealer_id=None, logger=None):
        self._id = str(uuid.uuid4())
        self._score_detector = score_detector
        self._logger = logger if logger else logging
        # Dictionary of players keyed by their ids
        self._players = {player.id: player for player in players}
        # List of player ids sorted according to the original players list
        self._player_ids = [player.id for player in players]
        # Current dealer
        self._dealer_id = dealer_id if dealer_id else self._player_ids[0]
        # Players who fold
        self._folder_ids = set()
        # Players who timed out or died
        self._dead_player_ids = set()
        # Game event subscribers
        self._event_subscribers = set()
        # Bets and pots
        self._bets = {player_id: 0.0 for player_id in self._player_ids}
        self._pots = []

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

    def init_player_hand(self, player):
        raise NotImplemented

    def dto(self):
        raise NotImplemented

    def _add_dead_player(self, player_id, error_message):
        player = self._players[player_id]
        self._logger.info("{}: {} error: {}".format(self, player, error_message))
        player.try_send_message({"message_type": "error", "error": error_message})
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
            # Not fun to play alone
            raise EndGameException()

    def _active_players_round(self, start_player_id):
        start_item = self._player_ids.index(start_player_id)
        for i in range(len(self._player_ids)):
            next_item = (i + start_item) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                yield player_id, self._players[player_id]
        raise StopIteration

    def _next_active_player_id(self, start_player_id):
        start_item = self._player_ids.index(start_player_id)
        for i in range(len(self._player_ids)):
            next_item = (i + start_item + 1) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                return player_id
        return None

    def _bet_round(self, dealer_id, bets):
        """Do a bet round. Returns the id of the player who made the strongest bet first."""

        player_ids = [player_id for player_id, _ in self._active_players_round(dealer_id)]
        player_ids.reverse()
        for k, player_id in enumerate(player_ids):
            if not bets.has_key(player_id):
                bets[player_id] = 0.0
            elif bets[player_id] < 0.0 or (k > 0 and bets[player_id] > bets[player_ids[k - 1]]):
                # Ensuring the bets dictionary makes sense
                raise ValueError("Invalid bets dictionary")

        # The player seated immediately before the dealer made the strongest bet (if any bet was made)
        best_player_id = player_ids[0] if bets[player_ids[0]] > 0.0 else None

        while dealer_id != best_player_id:

            if len(self._player_ids) - len(self._folder_ids) == 1:
                # Only one player left, break and do not ask for a bet
                # This can happen if during a bet round everybody fold and only the last player was left
                raise EndGameException

            # Two or more players still alive

            max_bet = self._get_max_bet(dealer_id, bets)

            min_bet = min(
                0.0 if best_player_id is None else bets[best_player_id] - bets[dealer_id],
                self._players[dealer_id].money
            )

            if max_bet == 0.0:
                # No bet required to this player
                bet = 0.0
            else:
                # This player isn't all in, and there's at least one other player who is not all-in
                bet, _ = self._player_bet(player_id=dealer_id, min_bet=min_bet, max_bet=max_bet)

            if bet != -1:
                bets[dealer_id] += bet

                if best_player_id is None or bet > min_bet:
                    best_player_id = dealer_id

            dealer_id = self._next_active_player_id(dealer_id)

        # Pots have been modified
        self._recalculate_pots()

        return best_player_id

    def _get_max_bet(self, dealer_id, bets):
        # Max raise:
        # Maximum amount of money that other players bet (or can still bet) during this round
        highest_stake = max(
            self._players[player_id].money + bets[player_id]
            for player_id in self._player_ids
            if player_id != dealer_id and player_id not in self._folder_ids
        )

        return min(
            highest_stake - bets[dealer_id],
            self._players[dealer_id].money
        )

    def _player_bet(self, player_id, min_bet, max_bet):
        try:
            player = self._players[player_id]
            timeout_epoch = time.time() + self.BET_TIMEOUT

            self._logger.info("{}: {} betting...".format(self, player))
            self._raise_event(
                Game.Event.PLAYER_ACTION,
                {
                    "action": "bet",
                    "min_bet": min_bet,
                    "max_bet": max_bet,
                    "player_id": player_id,
                    "timeout": self.BET_TIMEOUT,
                    "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
                }
            )

            bet = self._get_player_bet(
                player,
                min_bet=min_bet,
                max_bet=max_bet,
                timeout_epoch=timeout_epoch + self.TIMEOUT_TOLERANCE
            )
            bet_type = None

            if bet == -1:
                bet_type = "fold"
            elif bet == 0:
                bet_type = "check"
            else:
                player.take_money(bet)
                self._bets[player_id] += bet

                if not player.money:
                    bet_type = "all-in"
                elif bet == min_bet:
                    bet_type = "call"
                else:
                    bet_type = "raise"

            self._logger.info("{}: {} bet: {} ({})".format(self, player, bet, bet_type))
            self._raise_event(
                Game.Event.BET,
                {
                    "event": "bet",
                    "bet": bet,
                    "bet_type": bet_type,
                    "player_id": player_id
                }
            )

            if bet_type == "fold":
                self._add_folder(player_id)

            return bet, bet_type

        except (ChannelError, MessageFormatError, MessageTimeout) as e:
            self._add_dead_player(player_id, e.args[0])
            return -1, "fold"

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

    def _recalculate_pots(self):
        bets = dict(self._bets)

        # List of players sorted by their bets
        player_ids = sorted(
            self._player_ids,
            cmp=lambda player1_id, player2_id: cmp(bets[player1_id], bets[player2_id])
        )

        pots = []

        spare_money = 0.0

        for i in range(len(player_ids)):
            if player_ids[i] in self._folder_ids:
                # Current player fold, let's just put his money in the next pot
                spare_money += bets[player_ids[i]]
                bets[player_ids[i]] -= spare_money

            elif bets[player_ids[i]] > 0.0:
                # Current player is still active: there will be a new pot
                pot_player_ids = []
                pot_money = spare_money  # Money from previous players who fold will end up in this pot
                spare_money = 0.0

                # The amount that every player participating to this pot will have to put
                pot_bet = bets[player_ids[i]]

                # Going through all the remaining players who bet more than the current player
                # and collect money from them to build the current pot
                for j in range(i, len(player_ids)):
                    if player_ids[j] not in self._folder_ids:
                        # This player fold, he will not participate to this pot
                        pot_player_ids.append(player_ids[j])
                    pot_money += pot_bet
                    bets[player_ids[j]] -= pot_bet
                pots.append({
                    "player_ids": pot_player_ids,
                    "money": pot_money
                })

        self._pots = pots

    def _detect_winners(self):
        # Ensure pots are up to date
        self._recalculate_pots()

        for pot_index, pot in enumerate(self._pots):
            winners = []

            for player_id in pot["player_ids"]:
                player = self._players[player_id]

                if not winners:
                    winners.append(player)
                else:
                    score_diff = player.score.cmp(winners[0].score)
                    if score_diff == 0:
                        winners.append(player)
                    elif score_diff > 0:
                        winners = [player]

            # Split pot between the winners
            money = round(pot["money"] / len(winners), 2)
            for winner in winners:
                winner.add_money(money)

            self._logger.info("{}: pot {} (${}) won by {}".format(
                self,
                pot_index,
                pot["money"],
                ", ".join(str(winner) for winner in winners)
            ))
            pot["winner_ids"] = [player.id for player in winners]

            self._raise_event(
                Game.Event.WINNER_DESIGNATION,
                {"pot": pot_index}
            )

    def _raise_event(self, event, event_data=None):
        """Broadcast game events"""
        event_data = event_data if event_data else {}
        event_data["event"] = event
        game_data = self.dto()
        gevent.joinall([
            gevent.spawn(subscriber.game_event, event, event_data, game_data)
            for subscriber in self._event_subscribers
        ])
