from poker import *
import gevent
import logging
import math
import os
import random
import redis
import uuid


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


class HoldemPlayerClient:
    def __init__(self, player_connector, player, bet_strategy, logger):
        self._player_connector = player_connector
        self._player = player
        self._bet_strategy = bet_strategy
        self._logger = logger

    def play(self):
        # Connecting the player
        server_channel = self._player_connector.connect(self._player, str(uuid.uuid4()))

        cards_formatter = CardsFormatter(compact=True)

        room_players = {}
        game_players = None
        game_scores = None
        game_pot = None

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
                        if not room_players.has_key(player["id"]):
                            room_players[player["id"]] = Player(
                                id=player["id"],
                                name=player["name"],
                                money=player["money"]
                            )

                    if message["event"] == "player-removed":
                        del room_players[message["player_id"]]

                elif message["message_type"] == "game-update":
                    if message["event"] == "new-game":
                        game_players = GamePlayers([
                            room_players[player_id]
                            for player_id in message["player_ids"]
                        ])
                        game_scores = GameScores(HoldemPokerScoreDetector())
                        game_pot = 0.0
                        self._logger.info(u"{}: New game: {}".format(self._player, message["game_id"]))

                    elif message["event"] == "game-over":
                        game_players = None
                        game_scores = None
                        game_pot = None
                        self._logger.info(u"{}: Game over".format(self._player))

                    elif message["event"] == "set-cards":
                        cards = [Card(card[0], card[1]) for card in message["cards"]]
                        game_scores.assign_cards(self._player.id, cards)
                        self._logger.info(u"{}: Cards received: {}".format(
                            self._player,
                            cards_formatter.format(cards)
                        ))

                    elif message["event"] == "showdown":
                        for player_id in message["players"]:
                            cards = [Card(card[0], card[1]) for card in message["players"][player_id]["cards"]]
                            game_scores.assign_cards(player_id, cards)
                            self._logger.info(u"{}: {} cards: {}".format(
                                self._player,
                                game_players.get(player_id),
                                cards_formatter.format(cards))
                            )

                    elif message["event"] == "fold":
                        game_players.fold(message["player"]["id"])
                        self._logger.info(u"{}: {} fold".format(
                            self._player,
                            game_players.get(message["player"]["id"])
                        ))

                    elif message["event"] == "dead-player":
                        game_players.remove(message["player"]["id"])
                        self._logger.info(u"{}: {} left".format(
                            self._player,
                            game_players.get(message["player"]["id"])
                        ))

                    elif message["event"] == "pots-update":
                        game_pot = sum([pot["money"] for pot in message["pots"]])
                        self._logger.info(u"{}: Jackpot: ${:.2f}".format(self._player, game_pot))

                    elif message["event"] == "player-action" and message["action"] == "bet":
                        if message["player"]["id"] == self._player.id:
                            self._logger.info(u"{}: My turn to bet".format(self._player))
                            bet = self._bet_strategy.bet(
                                me=self._player,
                                game_players=game_players,
                                game_scores=game_scores,
                                game_pot=game_pot,
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
                                game_players.get(message["player"]["id"])
                            ))

                    elif message["event"] == "bet":
                        player = game_players.get(message["player"]["id"])
                        if message["bet"] > 0:
                            player.take_money(message["bet"])
                        self._logger.info(u"{}: {} bet ${:.2f} ({})".format(
                            self._player,
                            player,
                            message["bet"],
                            message["bet_type"]
                        ))

                    elif message["event"] == "shared-cards":
                        new_cards = [Card(card[0], card[1]) for card in message["cards"]]
                        game_scores.add_shared_cards(new_cards)
                        self._logger.info(u"{}: Shared cards: {}".format(
                            self._player,
                            cards_formatter.format(game_scores.shared_cards)
                        ))

                    elif message["event"] == "winner-designation":
                        self._logger.info("{}: ${:.2f} pot winners designation".format(
                            self._player,
                            message["pot"]["money"]
                        ))
                        for player_id in message["pot"]["winner_ids"]:
                            player = game_players.get(player_id)
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


class HandEvaluator:
    def __init__(self, score_detector):
        self.score_detector = score_detector

    def evaluate_cases(self, my_cards, shared_cards):
        all_cards = filter(
            lambda c: c not in my_cards and c not in shared_cards,
            [Card(rank, suit) for rank in range(2, 15) for suit in range(0, 4)]
        )
        my_score = self.score_detector.get_score(my_cards + shared_cards)

        wins = 0
        defeats = 0
        ties = 0

        for key1 in range(len(all_cards)):
            for key2 in range(key1 + 1, len(all_cards)):
                score = self.score_detector.get_score([all_cards[key1], all_cards[key2]] + shared_cards)
                score_diff = my_score.cmp(score)
                if score_diff > 0:
                    wins += 1
                elif score_diff == 0:
                    ties += 1
                else:
                    defeats += 1

        return wins, ties, defeats


class RandomBetStrategy:
    def __init__(self, fold_cases=2, call_cases=5, raise_cases=3):
        self._bet_cases = (["fold"] * fold_cases) + (["call"] * call_cases) + (["raise"] * raise_cases)

    def bet(self, me, game_players, game_scores, game_pot, bets, min_bet, max_bet):
        gevent.sleep(5 * random.random())   # 0 to 5 seconds

        decision = random.choice(self._bet_cases)

        if decision == "call" or (decision == "fold" and not min_bet):
            return min_bet

        elif decision == "fold":
            return -1

        else:
            max_raise = max_bet - min_bet
            return min_bet + math.floor(max_raise * random.random())


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO
    )
    logger = logging.getLogger()

    redis_url = os.environ["REDIS_URL"]
    redis = redis.from_url(redis_url)

    players = []

    player_connector = PlayerClientConnector(redis, "texas-holdem-poker:lobby", logger)

    for i in range(1, 4):
        player = Player(
            id="roboplayer-{}".format(i),
            name="Mr. Robot {}".format(i),
            money=1000.0
        )

        players.append(
            HoldemPlayerClient(
                player_connector=player_connector,
                player=player,
                bet_strategy=RandomBetStrategy(),
                logger=logger
            )
        )

    gevent.joinall([
        gevent.spawn(player.play)
        for player in players
    ])
