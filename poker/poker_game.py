import time
from typing import List, Dict, Set, Generator, Optional

import gevent

from .card import Card
from .channel import ChannelError, MessageTimeout, MessageFormatError
from .deck import DeckFactory, Deck
from .player import Player
from .player_server import PlayerServer
from .score_detector import Score, ScoreDetector


class GameError(Exception):
    pass


class EndGameException(Exception):
    pass


class GameFactory:
    def create_game(self, players: List[PlayerServer]):
        raise NotImplemented


class GameSubscriber:
    def game_event(self, event, event_data):
        raise NotImplemented


class GamePlayers:
    def __init__(self, players: List[Player]):
        # Dictionary of players keyed by their ids
        self._players: Dict[str, Player] = {player.id: player for player in players}
        # List of player ids sorted according to the original players list
        self._player_ids: List[str] = [player.id for player in players]
        # List of folder ids
        self._folder_ids: Set[str] = set()
        # Dead players
        self._dead_player_ids: Set[str] = set()

    def fold(self, player_id: str):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        self._folder_ids.add(player_id)

    def remove(self, player_id: str):
        self.fold(player_id)
        self._dead_player_ids.add(player_id)

    def reset(self):
        self._folder_ids = set(self._dead_player_ids)

    def round(self, start_player_id: str, reverse=False) -> Generator[Player, None, None]:
        start_item = self._player_ids.index(start_player_id)
        step_multiplier = -1 if reverse else 1
        for i in range(len(self._player_ids)):
            next_item = (start_item + (i * step_multiplier)) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                yield self._players[player_id]

    def get(self, player_id: str) -> Player:
        try:
            return self._players[player_id]
        except KeyError:
            raise ValueError("Unknown player id")

    def get_next(self, dealer_id: str) -> Optional[Player]:
        if dealer_id not in self._player_ids:
            raise ValueError("Unknown player id")
        if dealer_id in self._folder_ids:
            raise ValueError("Inactive player")
        start_item = self._player_ids.index(dealer_id)
        for i in range(len(self._player_ids) - 1):
            next_index = (start_item + i + 1) % len(self._player_ids)
            next_id = self._player_ids[next_index]
            if next_id not in self._folder_ids:
                return self._players[next_id]
        return None

    def is_active(self, player_id: str) -> bool:
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        return player_id not in self._folder_ids

    def count_active(self) -> int:
        return len(self._player_ids) - len(self._folder_ids)

    def count_active_with_money(self) -> int:
        return len([player for player in self.active if player.money > 0])

    @property
    def all(self) -> List[Player]:
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._dead_player_ids]

    @property
    def folders(self) -> List[Player]:
        return [self._players[player_id] for player_id in self._folder_ids]

    @property
    def dead(self) -> List[Player]:
        return [self._players[player_id] for player_id in self._dead_player_ids]

    @property
    def active(self) -> List[Player]:
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._folder_ids]


class GameScores:
    def __init__(self, score_detector: ScoreDetector):
        self._score_detector: ScoreDetector = score_detector
        self._players_cards: Dict[str, List[Card]] = {}
        self._shared_cards: List[Card] = []

    @property
    def shared_cards(self):
        return self._shared_cards

    def player_cards(self, player_id: str):
        return self._players_cards[player_id]

    def player_score(self, player_id: str):
        return self._score_detector.get_score(self._players_cards[player_id] + self._shared_cards)

    def assign_cards(self, player_id: str, cards: List[Card]):
        self._players_cards[player_id] = self._score_detector.get_score(cards).cards

    def add_shared_cards(self, cards):
        self._shared_cards += cards


class GamePots:
    class GamePot:
        def __init__(self):
            self._money = 0.0
            self._players: List[Player] = []

        def add_money(self, money: float):
            self._money += money

        def add_player(self, player: Player):
            self._players.append(player)

        @property
        def money(self) -> float:
            return self._money

        @property
        def players(self) -> List[Player]:
            return self._players

    def __len__(self):
        return len(self._pots)

    def __getitem__(self, item):
        return self._pots[item]

    def __iter__(self):
        return iter(self._pots)

    def __init__(self, game_players: GamePlayers):
        self._game_players = game_players
        self._pots = []
        self._bets = {player.id: 0.0 for player in game_players.all}

    def add_bets(self, bets: Dict[str, float]):
        for player in self._game_players.all:
            self._bets[player.id] += bets[player.id] if player.id in bets else 0.0

        bets = dict(self._bets)

        # List of players sorted by their bets
        players = sorted(
            self._game_players.all,
            key=lambda player: bets[player.id]
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


class GameEventDispatcher:
    def __init__(self, game_id: str, logger):
        self._subscribers: List[GameSubscriber] = []
        self._game_id: str = game_id
        self._logger = logger

    def subscribe(self, subscriber: GameSubscriber):
        self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber: GameSubscriber):
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

    def cards_assignment_event(self, player: Player, cards: List[Card], score: Score):
        self.raise_event(
            "cards-assignment",
            {
                "target": player.id,
                "cards": [card.dto() for card in cards],
                "score": score.dto()
            }
        )

    def pots_update_event(self, players: List[Player], pots: GamePots):
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

    def winner_designation_event(self, players: List[Player], pot: GamePots.GamePot, winners: List[Player], money_split: float, upcoming_pots: GamePots):
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

    def bet_action_event(self, player: Player, min_bet: float, max_bet: float, bets: Dict[str, float], timeout: int, timeout_epoch: float):
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

    def bet_event(self, player: Player, bet: float, bet_type: str, bets: Dict[str, float]):
        self.raise_event(
            "bet",
            {
                "player": player.dto(),
                "bet": bet,
                "bet_type": bet_type,
                "bets": bets
            }
        )

    def dead_player_event(self, player: Player):
        self.raise_event(
            "dead-player",
            {
                "player": player.dto()
            }
        )

    def fold_event(self, player: Player):
        self.raise_event(
            "fold",
            {
                "player": player.dto()
            }
        )

    def showdown_event(self, players: List[Player], scores: GameScores):
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


class GameWinnersDetector:
    def __init__(self, game_players: GamePlayers):
        self._game_players: GamePlayers = game_players

    def get_winners(self, players: List[Player], scores: GameScores) -> List[Player]:
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
    def __init__(self, game_players: GamePlayers):
        self._game_players: GamePlayers = game_players

    def _get_max_bet(self, dealer: Player, bets: Dict[str, float]) -> float:
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

    def _get_min_bet(self, dealer: Player, bets: Dict[str, float]) -> float:
        return min(
            max(bets.values()) - bets[dealer.id],
            dealer.money
        )

    def bet_round(self, dealer_id: str, bets: Dict[str, float], get_bet_function, on_bet_function=None) -> Optional[PlayerServer]:
        """
        performs a complete bet round
        returns the player who last raised - if nobody raised, then the first one to check
        """
        players_round = list(self._game_players.round(dealer_id))

        if len(players_round) == 0:
            raise GameError("No active players in this game")

        # The dealer might be inactive. Moving to the first active player
        dealer = players_round[0]

        for k, player in enumerate(players_round):
            if player.id not in bets:
                bets[player.id] = 0
            if bets[player.id] < 0 or (k > 0 and bets[player.id] < bets[players_round[k - 1].id]):
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
    def __init__(self, game_players: GamePlayers, bet_rounder: GameBetRounder, event_dispatcher: GameEventDispatcher, bet_timeout: int, timeout_tolerance: int, wait_after_round: int):
        self._game_players: GamePlayers = game_players
        self._bet_rounder: GameBetRounder = bet_rounder
        self._event_dispatcher: GameEventDispatcher = event_dispatcher
        self._bet_timeout: int = bet_timeout
        self._timeout_tolerance: int = timeout_tolerance
        self._wait_after_round: int = wait_after_round

    def any_bet(self, bets: Dict[str, float]) -> bool:
        return any(k for k in bets if bets[k] > 0)

    def bet_round(self, dealer_id: str, bets: Dict[str, float], pots: GamePots):
        best_player = self._bet_rounder.bet_round(dealer_id, bets, self.get_bet, self.on_bet)
        gevent.sleep(self._wait_after_round)
        if self.any_bet(bets):
            pots.add_bets(bets)
            self._event_dispatcher.pots_update_event(self._game_players.active, pots)
        return best_player

    def get_bet(self, player, min_bet: float, max_bet: float, bets: Dict[str, float]) -> Optional[int]:
        timeout_epoch = time.time() + self._bet_timeout
        self._event_dispatcher.bet_action_event(
            player=player,
            min_bet=min_bet,
            max_bet=max_bet,
            bets=bets,
            timeout=self._bet_timeout,
            timeout_epoch=timeout_epoch
        )
        return self.receive_bet(player, min_bet, max_bet, timeout_epoch)

    def receive_bet(self, player, min_bet, max_bet, timeout_epoch) -> Optional[int]:
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

    def on_bet(self, player: Player, bet: float, min_bet: float, max_bet: float, bets: Dict[str, float]):
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

    def __init__(self, id: str, game_players: GamePlayers, event_dispatcher: GameEventDispatcher, deck_factory: DeckFactory, score_detector: ScoreDetector):
        self._id: str = id
        self._game_players: GamePlayers = game_players
        self._event_dispatcher: GameEventDispatcher = event_dispatcher
        self._deck_factory: DeckFactory = deck_factory
        self._score_detector: ScoreDetector = score_detector
        self._bet_handler: GameBetHandler = self._create_bet_handler()
        self._winners_detector: GameWinnersDetector = self._create_winners_detector()

    @property
    def event_dispatcher(self) -> GameEventDispatcher:
        return self._event_dispatcher

    def play_hand(self, dealer_id: str):
        raise NotImplemented

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Factory methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _create_bet_handler(self) -> GameBetHandler:
        return GameBetHandler(
            game_players=self._game_players,
            bet_rounder=GameBetRounder(self._game_players),
            event_dispatcher=self._event_dispatcher,
            bet_timeout=self.BET_TIMEOUT,
            timeout_tolerance=self.TIMEOUT_TOLERANCE,
            wait_after_round=self.WAIT_AFTER_BET_ROUND
        )

    def _create_winners_detector(self) -> GameWinnersDetector:
        return GameWinnersDetector(self._game_players)

    def _create_pots(self) -> GamePots:
        return GamePots(self._game_players)

    def _create_scores(self) -> GameScores:
        return GameScores(self._score_detector)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Cards handler
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _assign_cards(self, number_of_cards: int, dealer_id: str, deck: Deck, scores: GameScores):
        # Assign cards
        for player in self._game_players.round(dealer_id):
            # Distribute cards
            scores.assign_cards(player.id, deck.pop_cards(number_of_cards))
            self._send_player_score(player, scores)
        gevent.sleep(self.WAIT_AFTER_CARDS_ASSIGNMENT)

    def _send_player_score(self, player: Player, scores: GameScores):
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

    def _detect_winners(self, pots: GamePots, scores: GameScores):
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

    def _showdown(self, scores: GameScores):
        self._event_dispatcher.showdown_event(self._game_players.active, scores)
        gevent.sleep(self.WAIT_AFTER_SHOWDOWN)
