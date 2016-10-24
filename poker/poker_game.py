from . import ChannelError, MessageTimeout, MessageFormatError
import gevent
import time


class GameError(Exception):
    pass


class EndGameException(Exception):
    pass


class GameFactory:
    def create_game(self, players):
        raise NotImplemented


class GameSubscriber:
    def game_event(self, event, event_data):
        raise NotImplemented


class GameEventDispatcher:
    def __init__(self, game_id, logger):
        self._subscribers = []
        self._game_id = game_id
        self._logger = logger

    def subscribe(self, subscriber):
        self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber):
        self._subscribers.remove(subscriber)

    def raise_event(self, event, event_data):
        event_data["event"] = event
        event_data["game_id"] = self._game_id
        self._logger.debug(
            "\n" +
            ("-" * 80) + "\n"
            "GAME: {}\nEVENT: {}".format(self._game_id, event) + "\n" +
            str(event_data) + "\n" +
            ("-" * 80) + "\n"
        )
        gevent.joinall([
            gevent.spawn(subscriber.game_event, event, event_data)
            for subscriber in self._subscribers
        ])

    def cards_assignment_event(self, player, cards, score):
        self.raise_event(
            "cards-assignment",
            {
                "target": player.id,
                "cards": [card.dto() for card in cards],
                "score": score.dto()
            }
        )

    def pots_update_event(self, players, pots):
        self.raise_event(
            "pots-update",
            {
                "pots": [
                    {
                        "money": pot.money,
                        "player_ids": [player.id for player in pot.players],
                    }
                    for pot in pots
                ],
                "players": {player.id: player.dto() for player in players}
            }
        )

    def winner_designation_event(self, players, pot, winners, money_split, upcoming_pots):
        self.raise_event(
            "winner-designation",
            {
                "pot": {
                    "money": pot.money,
                    "player_ids": [player.id for player in pot.players],
                    "winner_ids": [winner.id for winner in winners],
                    "money_split": money_split
                },
                "pots": [
                    {
                        "money": upcoming_pot.money,
                        "player_ids": [player.id for player in upcoming_pot.players]
                    }
                    for upcoming_pot in upcoming_pots
                ],
                "players": {player.id: player.dto() for player in players}
            }
        )

    def bet_action_event(self, player, min_bet, max_bet, bets, timeout, timeout_epoch):
        self.raise_event(
            "player-action",
            {
                "action": "bet",
                "player": player.dto(),
                "min_bet": min_bet,
                "max_bet": max_bet,
                "bets": bets,
                "timeout": timeout,
                "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
            }
        )

    def bet_event(self, player, bet, bet_type, bets):
        self.raise_event(
            "bet",
            {
                "player": player.dto(),
                "bet": bet,
                "bet_type": bet_type,
                "bets": bets
            }
        )

    def dead_player_event(self, player):
        self.raise_event(
            "dead-player",
            {
                "player": player.dto()
            }
        )

    def fold_event(self, player):
        self.raise_event(
            "fold",
            {
                "player": player.dto()
            }
        )

    def showdown_event(self, players, scores):
        self.raise_event(
            "showdown",
            {
                "players": {
                    player.id: {
                        "cards": [card.dto() for card in scores.player_cards(player.id)],
                        "score": scores.player_score(player.id).dto(),
                    }
                    for player in players
                }
            }
        )


class GamePlayers:
    def __init__(self, players):
        # Dictionary of players keyed by their ids
        self._players = {player.id: player for player in players}
        # List of player ids sorted according to the original players list
        self._player_ids = [player.id for player in players]
        # List of folder ids
        self._folder_ids = set()
        # Dead players
        self._dead_player_ids = set()

    def fold(self, player_id):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        self._folder_ids.add(player_id)

    def remove(self, player_id):
        self.fold(player_id)
        self._dead_player_ids.add(player_id)

    def reset(self):
        self._folder_ids = set(self._dead_player_ids)

    def round(self, start_player_id, reverse=False):
        start_item = self._player_ids.index(start_player_id)
        step_multiplier = -1 if reverse else 1
        for i in range(len(self._player_ids)):
            next_item = (start_item + (i * step_multiplier)) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                yield self._players[player_id]
        raise StopIteration

    # def rounder(self, start_player_id):
    #     def decorator(action):
    #         def perform():
    #             start_item = self._player_ids.index(start_player_id)
    #             try:
    #                 while True:
    #                     player_id = self._player_ids[start_item]
    #                     if player_id not in self._folder_ids:
    #                         action(self._players[player_id])
    #                     start_item = (start_item + 1) % len(self._player_ids)
    #             except StopIteration:
    #                 pass
    #         return perform
    #     return decorator

    def get(self, player_id):
        try:
            return self._players[player_id]
        except KeyError:
            raise ValueError("Unknown player id")

    def get_next(self, player_id):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        if player_id in self._folder_ids:
            raise ValueError("Inactive player")
        start_item = self._player_ids.index(player_id)
        for i in range(len(self._player_ids) - 1):
            next_index = (start_item + i + 1) % len(self._player_ids)
            next_id = self._player_ids[next_index]
            if next_id not in self._folder_ids:
                return self._players[next_id]
        return None

    def get_previous(self, player_id):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        if player_id in self._folder_ids:
            raise ValueError("Inactive player")
        start_index = self._player_ids.index(player_id)
        for i in range(len(self._player_ids) - 1):
            previous_index = (start_index - i - 1) % len(self._player_ids)
            previous_id = self._player_ids[previous_index]
            if previous_id not in self._folder_ids:
                return self._players[previous_id]
        return None

    def is_active(self, player_id):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        return player_id not in self._folder_ids

    def count_active(self):
        return len(self._player_ids) - len(self._folder_ids)

    def count_active_with_money(self):
        return len(filter(lambda player: player.money > 0, self.active))

    @property
    def all(self):
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._dead_player_ids]

    @property
    def folders(self):
        return [self._players[player_id] for player_id in self._folder_ids]

    @property
    def dead(self):
        return [self._players[player_id] for player_id in self._dead_player_ids]

    @property
    def active(self):
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._folder_ids]


class GamePots:
    class GamePot:
        def __init__(self):
            self._money = 0.0
            self._players = []

        def add_money(self, money):
            self._money += money

        def add_player(self, player):
            self._players.append(player)

        @property
        def money(self):
            return self._money

        @property
        def players(self):
            return self._players

    def __len__(self):
        return len(self._pots)

    def __getitem__(self, item):
        return self._pots[item]

    def __iter__(self):
        return iter(self._pots)

    def __init__(self, game_players):
        self._game_players = game_players
        self._pots = []
        self._bets = {player.id: 0.0 for player in game_players.all}

    def add_bets(self, bets):
        for player in self._game_players.all:
            self._bets[player.id] += bets[player.id] if bets.has_key(player.id) else 0.0

        bets = dict(self._bets)

        # List of players sorted by their bets
        players = sorted(
            self._game_players.all,
            cmp=lambda player1, player2: cmp(bets[player1.id], bets[player2.id])
        )

        self._pots = []

        spare_money = 0.0

        for i, player in enumerate(players):
            if not self._game_players.is_active(player.id):
                # Inactive players don't take part to any pot
                spare_money += bets[player.id]
                bets[player.id] = 0.0
            elif bets[player.id] > 0.0:
                pot_bet = bets[player.id]
                current_pot = GamePots.GamePot()
                # Collecting spare money coming from previous inactive players
                current_pot.add_money(spare_money)
                spare_money = 0.0
                for j in range(i, len(players)):
                    if self._game_players.is_active(players[j].id):
                        # This player will participate to this pot only if currently active
                        current_pot.add_player(players[j])
                    current_pot.add_money(pot_bet)
                    bets[players[j].id] -= pot_bet
                self._pots.append(current_pot)

        if spare_money:
            # The players who bet more is actually inactive
            raise ValueError("Invalid bets")


class GameScores:
    def __init__(self, score_detector):
        self._score_detector = score_detector
        self._players_cards = {}
        self._shared_cards = []

    @property
    def shared_cards(self):
        return self._shared_cards

    def player_cards(self, player_id):
        return self._players_cards[player_id]

    def player_score(self, player_id):
        return self._score_detector.get_score(self._players_cards[player_id] + self._shared_cards)

    def assign_cards(self, player_id, cards):
        self._players_cards[player_id] = self._score_detector.get_score(cards).cards

    def add_shared_cards(self, cards):
        self._shared_cards += cards


class GameWinnersDetector:
    def __init__(self, game_players):
        self._game_players = game_players

    def get_winners(self, players, scores):
        winners = []

        for player in players:
            if not self._game_players.is_active(player.id):
                continue
            if not winners:
                winners.append(player)
            else:
                score_diff = scores.player_score(player.id).cmp(scores.player_score(winners[0].id))
                if score_diff == 0:
                    winners.append(player)
                elif score_diff > 0:
                    winners = [player]

        return winners


class GameBetRounder:
    def __init__(self, game_players):
        self._game_players = game_players

    def _get_max_bet(self, dealer, bets):
        # Max raise:
        # Maximum amount of money that other players bet (or can still bet) during this round
        try:
            highest_stake = max(
                player.money + bets[player.id]
                for player in self._game_players.round(dealer.id)
                if player is not dealer
            )
        except ValueError:
            return 0.0

        return min(
            highest_stake - bets[dealer.id],
            dealer.money
        )

    def _get_min_bet(self, dealer, bets):
        return min(
            max(bets.values()) - bets[dealer.id],
            dealer.money
        )

    def bet_round(self, dealer_id, bets, get_bet_function, on_bet_function=None):
        players_round = list(self._game_players.round(dealer_id))

        if len(players_round) == 0:
            raise GameError("No active players in this game")

        # The dealer might be inactive. Moving to the first active player
        dealer = players_round[0]

        for k, player in enumerate(players_round):
            if not bets.has_key(player.id):
                bets[player.id] = 0.0
            if bets[player.id] < 0.0 or (k > 0 and bets[player.id] < bets[players_round[k - 1].id]):
                # Ensuring the bets dictionary makes sense
                raise ValueError("Invalid bets dictionary")

        best_player = None

        while dealer is not None and dealer != best_player:
            next_player = self._game_players.get_next(dealer.id)

            max_bet = self._get_max_bet(dealer, bets)
            min_bet = self._get_min_bet(dealer, bets)

            if max_bet == 0.0:
                # No bet required to this player (either he is all-in or all other players are all-in)
                bet = 0.0
            else:
                # This player isn't all in, and there's at least one other player who is not all-in
                bet = get_bet_function(player=dealer, min_bet=min_bet, max_bet=max_bet, bets=bets)

            if bet is None:
                self._game_players.remove(dealer.id)
            elif bet == -1:
                self._game_players.fold(dealer.id)
            else:
                if bet < min_bet or bet > max_bet:
                    raise ValueError("Invalid bet")
                dealer.take_money(bet)
                bets[dealer.id] += bet
                if best_player is None or bet > min_bet:
                    best_player = dealer

            if on_bet_function:
                on_bet_function(dealer, bet, min_bet, max_bet, bets)

            dealer = next_player
        return best_player


class GameBetHandler:
    def __init__(self, game_players, bet_rounder, event_dispatcher, bet_timeout, timeout_tolerance, wait_after_round):
        self._game_players = game_players
        self._bet_rounder = bet_rounder
        self._event_dispatcher = event_dispatcher
        self._bet_timeout = bet_timeout
        self._timeout_tolerance = timeout_tolerance
        self._wait_after_round = wait_after_round

    def any_bet(self, bets):
        return any(k for k in bets if bets[k] > 0)

    def bet_round(self, dealer_id, bets, pots):
        best_player = self._bet_rounder.bet_round(dealer_id, bets, self.get_bet, self.on_bet)
        gevent.sleep(self._wait_after_round)
        if self.any_bet(bets):
            pots.add_bets(bets)
            self._event_dispatcher.pots_update_event(self._game_players.active, pots)
        return best_player

    def get_bet(self, player, min_bet, max_bet, bets):
        timeout_epoch = time.time() + self._bet_timeout
        self._event_dispatcher.bet_action_event(
            player=player,
            min_bet=min_bet,
            max_bet=max_bet,
            bets=bets,
            timeout=self._bet_timeout,
            timeout_epoch=timeout_epoch
        )
        return self.receive_bet(player, min_bet, max_bet, bets, timeout_epoch)

    def receive_bet(self, player, min_bet, max_bet, bets, timeout_epoch):
        try:
            message = player.recv_message(timeout_epoch=timeout_epoch)

            MessageFormatError.validate_message_type(message, "bet")

            if "bet" not in message:
                raise MessageFormatError(attribute="bet", desc="Attribute is missing")

            try:
                bet = round(float(message["bet"]))  # Strip decimals
            except ValueError:
                raise MessageFormatError(attribute="bet", desc="'{}' is not a number".format(message.bet))
            else:
                # Validating bet
                if bet != -1 and (bet < min_bet or bet > max_bet):
                    raise MessageFormatError(
                        attribute="bet",
                        desc="Bet out of range. min: {} max: {}, actual: {}".format(min_bet, max_bet, bet)
                    )
                return bet

        except (ChannelError, MessageFormatError, MessageTimeout) as e:
            player.send_message({"message_type": "error", "error": e.args[0]})
            return None

    def on_bet(self, player, bet, min_bet, max_bet, bets):
        def get_bet_type(bet):
            if bet == 0:
                return "check"
            elif bet == player.money:
                return "all-in"
            elif bet == min_bet:
                return "call"
            else:
                return "raise"

        if bet is None:
            self._event_dispatcher.dead_player_event(player)
        elif bet == -1:
            self._event_dispatcher.fold_event(player)
        else:
            self._event_dispatcher.bet_event(player, bet, get_bet_type(bet), bets)


class PokerGame:
    TIMEOUT_TOLERANCE = 2
    BET_TIMEOUT = 30

    WAIT_AFTER_CARDS_ASSIGNMENT = 1
    WAIT_AFTER_BET_ROUND = 1
    WAIT_AFTER_SHOWDOWN = 2
    WAIT_AFTER_WINNER_DESIGNATION = 5

    def __init__(self, id, game_players, event_dispatcher, deck_factory, score_detector):
        self._id = id
        self._game_players = game_players
        self._event_dispatcher = event_dispatcher
        self._deck_factory = deck_factory
        self._score_detector = score_detector
        self._bet_handler = self._create_bet_handler()
        self._winners_detector = self._create_winners_detector()

    @property
    def event_dispatcher(self):
        return self._event_dispatcher

    def play_hand(self, dealer_id):
        raise NotImplemented

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Factory methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _create_bet_handler(self):
        return GameBetHandler(
            game_players=self._game_players,
            bet_rounder=GameBetRounder(self._game_players),
            event_dispatcher=self._event_dispatcher,
            bet_timeout=self.BET_TIMEOUT,
            timeout_tolerance=self.TIMEOUT_TOLERANCE,
            wait_after_round=self.WAIT_AFTER_BET_ROUND
        )

    def _create_winners_detector(self):
        return GameWinnersDetector(self._game_players)

    def _create_pots(self):
        return GamePots(self._game_players)

    def _create_scores(self):
        return GameScores(self._score_detector)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Cards handler
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _assign_cards(self, number_of_cards, dealer_id, deck, scores):
        # Assign cards
        for player in self._game_players.round(dealer_id):
            # Distribute cards
            scores.assign_cards(player.id, deck.pop_cards(number_of_cards))
            self._send_player_score(player, scores)
        gevent.sleep(self.WAIT_AFTER_CARDS_ASSIGNMENT)

    def _send_player_score(self, player, scores):
        self._event_dispatcher.cards_assignment_event(
            player=player,
            cards=scores.player_cards(player.id),
            score=scores.player_score(player.id)
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Winners designation
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _game_over_detection(self):
        if self._game_players.count_active() < 2:
            raise EndGameException

    def _detect_winners(self, pots, scores):
        for i, pot in enumerate(reversed(pots)):
            winners = self._winners_detector.get_winners(pot.players, scores)
            try:
                money_split = round(pot.money / len(winners))  # Strip decimals
            except ZeroDivisionError:
                raise GameError("No players left")
            else:
                for winner in winners:
                    winner.add_money(money_split)

                self._event_dispatcher.winner_designation_event(
                    players=self._game_players.active,
                    pot=pot,
                    winners=winners,
                    money_split=money_split,
                    upcoming_pots=pots[(i + 1):]
                )

                gevent.sleep(self.WAIT_AFTER_WINNER_DESIGNATION)

    def _showdown(self, scores):
        self._event_dispatcher.showdown_event(self._game_players.active, scores)
        gevent.sleep(self.WAIT_AFTER_SHOWDOWN)
