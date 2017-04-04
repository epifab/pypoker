from poker import *
import bisect
import gevent
import logging.handlers
import math
import os
import random
import redis
import uuid


def get_random_name():
    names = [
        "Johnny", "Thomas", "Walter", "Brian", "Doyle", "Bobby", "Hal", "Stu", "Jack", "Tom", "Jack", "Bill", "Barry",
        "Phil", "Mansour", "Brad", "Hamid", "Jim", "Russ", "Dan", "Huck", "Scotty", "Noel", "Chris", "Carlos", "Robert",
        "Chris", "Greg", "Joe", "Jamie", "Jerry", "Peter", "Joe", "Jonathan", "Pius", "Greg", "Ryan", "Martin", "Joe",
    ]
    surnames = [
        "Moss", "Preston", "Pearson", "Roberts", "Brunson", "Baldwin", "Fowler", "Ungar", "Straus", "McEvoy", "Keller",
        "Smith", "Johnston", "Chan", "Hellmuth", "Matloubi", "Daugherty", "Dastmalchi", "Bechtel", "Hamilton",
        "Harrington", "Seed", "Nguyen", "Furlong", "Ferguson", "Mortensen", "Varkonyi", "Moneymaker", "Raymer",
        "Hachem", "Gold", "Yang", "Eastgate", "Cada", "Duhamel", "Heinz", "Merson", "Riess", "Jacobson"
    ]
    return random.choice(names) + " " + random.choice(surnames)


class CardsFormatter:
    def __init__(self, compact=True):
        self.compact = compact

    def format(self, cards):
        return self.compact_format(cards) if self.compact else self.visual_format(cards)

    def compact_format(self, cards):
        return u" ".join(
            u"[{} of {}]".format(Card.RANKS[card.rank], Card.SUITS[card.suit])
            for card in cards
        )

    def visual_format(self, cards):
        lines = [""] * 7
        for card in cards:
            lines[0] += u"+-------+"
            lines[1] += u"| {:<2}    |".format(Card.RANKS[card.rank])
            lines[2] += u"|       |"
            lines[3] += u"|   {}   |".format(Card.SUITS[card.suit])
            lines[4] += u"|       |"
            lines[5] += u"|    {:>2} |".format(Card.RANKS[card.rank])
            lines[6] += u"+-------+"
        return u"\n".join(lines)


class HoldemGameState:
    STATE_PREFLOP = 0
    STATE_FLOP = 1
    STATE_TURN = 2
    STATE_RIVER = 3

    def __init__(self, players, scores, pot, big_blind, small_blind):
        self.players = players
        self.scores = scores
        self.pot = pot
        self.big_blind = big_blind
        self.small_blind = small_blind
        self.bets = {}

    @property
    def state(self):
        num_shared_cards = len(self.scores.shared_cards)
        if num_shared_cards == 0:
            return HoldemGameState.STATE_PREFLOP
        elif num_shared_cards == 3:
            return HoldemGameState.STATE_FLOP
        elif num_shared_cards == 4:
            return HoldemGameState.STATE_TURN
        else:
            return HoldemGameState.STATE_RIVER


class HoldemPlayerClient:
    def __init__(self, player_connector, player, bet_strategy, logger):
        self._player_connector = player_connector
        self._player = player
        self._bet_strategy = bet_strategy
        self._logger = logger

    def play_forever(self):
        while True:
            self.play()
            gevent.sleep(5)

    def play(self):
        # Connecting the player
        server_channel = self._player_connector.connect(self._player, str(uuid.uuid4()))

        cards_formatter = CardsFormatter(compact=True)

        room_players = {}
        game_state = None

        while True:
            try:
                message = server_channel.recv_message(time.time() + 120)  # Wait for max 2 minutes
            except MessageTimeout:
                server_channel.send_message({"message_type": "disconnect"})
                self._logger.info("{}: Server did not send anything in 2 minutes: disconnecting".format(
                    self._player
                ))
                break
            else:
                if message["message_type"] == "disconnect":
                    self._logger.info("{}: Disconnected from the server".format(self._player))
                    break

                elif message["message_type"] == "ping":
                    server_channel.send_message({"message_type": "pong"})

                elif message["message_type"] == "room-update":
                    for player in message["players"].values():
                        if player["id"] not in room_players:
                            room_players[player["id"]] = Player(
                                id=player["id"],
                                name=player["name"],
                                money=player["money"]
                            )

                    if message["event"] == "player-removed":
                        del room_players[message["player_id"]]

                elif message["message_type"] == "game-update":
                    if message["event"] == "new-game":
                        game_state = HoldemGameState(
                            players=GamePlayers([
                                room_players[player["id"]]
                                for player in message["players"]
                            ]),
                            scores=GameScores(HoldemPokerScoreDetector()),
                            pot=0.0,
                            big_blind=message["big_blind"],
                            small_blind=message["small_blind"]
                        )
                        self._logger.info(u"{}: New game: {}".format(self._player, message["game_id"]))

                    elif message["event"] == "game-over":
                        game_state = None
                        self._logger.info(u"{}: Game over".format(self._player))

                    elif message["event"] == "cards-assignment":
                        cards = [Card(card[0], card[1]) for card in message["cards"]]
                        game_state.scores.assign_cards(self._player.id, cards)
                        self._logger.info(u"{}: Cards received: {}".format(
                            self._player,
                            cards_formatter.format(cards)
                        ))

                    elif message["event"] == "showdown":
                        for player_id in message["players"]:
                            cards = [Card(card[0], card[1]) for card in message["players"][player_id]["cards"]]
                            game_state.scores.assign_cards(player_id, cards)
                            self._logger.info(u"{}: {} cards: {}".format(
                                self._player,
                                game_state.players.get(player_id),
                                cards_formatter.format(cards))
                            )

                    elif message["event"] == "fold":
                        game_state.players.fold(message["player"]["id"])
                        self._logger.info(u"{}: {} fold".format(
                            self._player,
                            game_state.players.get(message["player"]["id"])
                        ))

                    elif message["event"] == "dead-player":
                        game_state.players.remove(message["player"]["id"])
                        self._logger.info(u"{}: {} left".format(
                            self._player,
                            game_state.players.get(message["player"]["id"])
                        ))

                    elif message["event"] == "pots-update":
                        game_state.pot = sum([pot["money"] for pot in message["pots"]])
                        self._logger.info(u"{}: Jackpot: ${:.2f}".format(self._player, game_state.pot))

                    elif message["event"] == "player-action" and message["action"] == "bet":
                        if message["player"]["id"] == self._player.id:
                            self._logger.info(u"{}: My turn to bet".format(self._player))
                            bet = self._bet_strategy.bet(
                                me=self._player,
                                game_state=game_state,
                                min_bet=message["min_bet"],
                                max_bet=message["max_bet"],
                                bets=message["bets"]
                            )

                            server_channel.send_message({
                                "message_type": "bet",
                                "bet": bet
                            })
                            if bet == -1:
                                self._logger.info("{}: Will fold".format(self._player))
                            elif bet == 0:
                                self._logger.info("{}: Will check".format(self._player))
                            elif bet == message["min_bet"]:
                                self._logger.info("{}: Will call ${:.2f}".format(self._player, bet))
                            elif bet == message["max_bet"]:
                                self._logger.info("{}: Will raise to ${:.2f}".format(self._player, bet))

                        else:
                            self._logger.info(u"{}: waiting for {} to bet...".format(
                                self._player,
                                game_state.players.get(message["player"]["id"])
                            ))

                    elif message["event"] == "bet":
                        player = game_state.players.get(message["player"]["id"])
                        player.take_money(message["bet"])
                        self._logger.info(u"{}: {} bet ${:.2f} ({})".format(
                            self._player,
                            player,
                            message["bet"],
                            message["bet_type"]
                        ))

                    elif message["event"] == "shared-cards":
                        new_cards = [Card(card[0], card[1]) for card in message["cards"]]
                        game_state.scores.add_shared_cards(new_cards)
                        self._logger.info(u"{}: Shared cards: {}".format(
                            self._player,
                            cards_formatter.format(game_state.scores.shared_cards)
                        ))

                    elif message["event"] == "winner-designation":
                        self._logger.info("{}: ${:.2f} pot winners designation".format(
                            self._player,
                            message["pot"]["money"]
                        ))
                        for player_id in message["pot"]["winner_ids"]:
                            player = game_state.players.get(player_id)
                            player.add_money(message["pot"]["money_split"])
                            self._logger.info("{}: {} won ${:.2f}".format(
                                self._player,
                                player,
                                message["pot"]["money_split"]
                            ))

                    else:
                        self._logger.error("{}: Event {} not recognised".format(
                            self._player,
                            message["event"]
                        ))

                else:
                    self._logger.error("{}: Message type {} not recognised".format(
                        self._player,
                        message["message_type"]
                    ))


class RandomBetStrategy:
    def __init__(self, fold_cases=2, call_cases=5, raise_cases=3):
        self._bet_cases = (["fold"] * fold_cases) + (["call"] * call_cases) + (["raise"] * raise_cases)

    def bet(self, me, game_state, bets, min_bet, max_bet):
        decision = random.choice(self._bet_cases)

        gevent.sleep(5)

        if decision == "call" or (decision == "fold" and not min_bet):
            return min_bet

        elif decision == "fold":
            return -1

        else:
            max_raise = max_bet - min_bet
            return min_bet + math.floor(max_raise * random.random())


class SmartBetStrategy:
    def __init__(self, hand_evaluator, logger):
        self.hand_evaluator = hand_evaluator
        self.logger = logger

    @staticmethod
    def choice(population, weights):
        def cdf(weights):
            total = sum(weights)
            result = []
            cumsum = 0
            for w in weights:
                cumsum += w
                result.append(cumsum / total)
            return result

        assert len(population) == len(weights)
        cdf_vals = cdf(weights)
        x = random.random()
        idx = bisect.bisect(cdf_vals, x)
        return population[idx]

    def bet(self, me, game_state, bets, min_bet, max_bet):
        num_shared_cards = len(game_state.scores.shared_cards)
        num_followers = game_state.players.count_active_with_money() - (1 if me.money else 0)
        max_raise = max_bet - min_bet
        game_pot = game_state.pot + sum(bets.values())

        cards_formatter = CardsFormatter(compact=False)
        self.logger.info(u"{}: My cards:\n{}".format(
            me,
            cards_formatter.format(game_state.scores.player_cards(me.id))
        ))
        if num_shared_cards:
            self.logger.info(u"{}: Board cards:\n{}".format(
                me,
                cards_formatter.format(game_state.scores.shared_cards)
            ))
        self.logger.info("{}: Min bet: ${:.2f} - Max bet: ${:.2f}".format(me, min_bet, max_bet))
        self.logger.info("{}: Max raise: ${:.2f}".format(me, max_raise))
        self.logger.info("{}: Pots: ${:.2f}".format(me, game_pot))
        self.logger.info("{}: Number of followers: {}".format(me, num_followers))

        if game_state.state == HoldemGameState.STATE_PREFLOP:
            hand_strength = self.hand_evaluator.hand_strength(
                my_cards=game_state.scores.player_cards(me.id),
                board=game_state.scores.shared_cards,
                num_followers=num_followers,
                timeout=5
            )
        else:
            hand_strength = self.hand_evaluator.hand_strength(
                my_cards=game_state.scores.player_cards(me.id),
                board=game_state.scores.shared_cards,
                num_followers=num_followers,
                timeout=8
            )

        self.logger.info("{}: Hand strength: {}".format(me, hand_strength))

        # pot_odds = min_bet / (min_bet + game_pot)
        #
        # rate_of_return = hand_strength / pot_odds
        # self.logger.info("{}: Rate of return: {}".format(me, rate_of_return))

        choices = ["fold", "call", "raise"]

        # Rate between big blind and the call bet
        call_rate = game_state.big_blind / (game_state.big_blind + min_bet)
        # Between 0 and 1: 0: not great to call, 1: very valuable
        pot_size = game_pot / game_state.big_blind

        if hand_strength < 0.10:
            # Mostly fold
            if call_rate > 0.85:
                weights = [0.65, 0.30, 0.05]
            elif call_rate > 0.5:
                weights = [0.80, 0.15, 0.05]
            else:
                weights = [0.95, 0.00, 0.05]
        elif hand_strength < 0.20:
            # Mostly fold/call
            if call_rate > 0.85:
                weights = [0.45, 0.50, 0.05]
            elif call_rate > 0.5:
                weights = [0.60, 0.35, 0.05]
            else:
                weights = [0.75, 0.20, 0.05]
        elif hand_strength < 0.35:
            # Mostly call
            if call_rate > 0.85:
                weights = [0.00, 0.70, 0.30]
            elif call_rate > 0.5:
                weights = [0.15, 0.65, 0.20]
            else:
                weights = [0.40, 0.55, 0.05]
        elif hand_strength < 0.50:
            weights = [0.00, 0.45, 0.55]
        else:
            weights = [0.00, 0.25, 0.75]

        self.logger.info("{}: Fold: {}%, Call: {}%, Raise: {}%".format(me, weights[0], weights[1], weights[2]))

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #  DECISION
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        choice = self.choice(choices, weights)

        if choice == "call" or (choice == "fold" and min_bet == 0.0) or (choice == "raise" and max_raise == 0.0):
            bet = min_bet
        elif choice == "fold":
            bet = -1
        else:
            # Raise
            raises = 1 + int(round(max_raise / game_state.big_blind))
            bet = min_bet + (float(random.choice(range(1, raises + 1))) / float(raises) * max_raise)

        self.logger.info("{}: I decided to {} (${:.2f})".format(me, choice, bet))
        return bet


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)

    redis_url = os.environ["REDIS_URL"]
    redis = redis.from_url(redis_url)

    player_connector = PlayerClientConnector(redis, "texas-holdem-poker:lobby", logging)

    while True:
        player_id = str(uuid.uuid4())

        logger = logging.getLogger("player-{}".format(player_id))
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.handlers.WatchedFileHandler(
            filename="logs/bet-strategy-virtual-player-{}.log".format(player_id),
            mode='a'
        ))

        player = Player(
            id="hal-{}".format(str(uuid.uuid4())),
            name=get_random_name(),
            money=1000.0
        )

        virtual_player = HoldemPlayerClient(
            player_connector=player_connector,
            player=player,
            # bet_strategy=RandomBetStrategy(call_cases=7, fold_cases=2, raise_cases=1),
            bet_strategy=SmartBetStrategy(HandEvaluator(HoldemPokerScoreDetector()), logger),
            logger=logger
        )

        virtual_player.play()
