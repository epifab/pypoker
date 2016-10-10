from . import Game, GameFactory, Card, Deck, ScoreDetector, EndGameException, \
    ChannelError, MessageTimeout, MessageFormatError
import gevent
import time


class HoldemGame(Game):
    def __init__(self, players, deck, score_detector, small_blind=10.0, big_lind=20.0, dealer_id=None, logger=None):
        Game.__init__(
            self,
            players=players,
            dealer_id=dealer_id,
            logger=logger
        )
        self._deck = deck
        self._score_detector = score_detector
        # Small and big blind
        self._small_blind = small_blind
        self._big_blind = big_lind
        # Current pot
        self._pot = 0.0
        # Current bets for each player (sum of _bets is always equal to _pot)
        self._bets = {player_id: 0.0 for player_id in self._player_ids}
        self._shared_cards = []

    def _collect_blinds(self):
        raise NotImplemented

    def _assign_cards(self):
        raise NotImplemented

    def _evaluate_scores(self):
        raise

    def play_hand(self):
        try:
            # Initialization
            self._deck.initialize()
            self._player_ids_allowed_to_open = set()
            self._player_ids_show_cards = set()

            self._check_active_players()

            # Initial bet for every player
            self._collect_blinds()

            # Cards assignment
            self._logger.info("{}: [[cards assignment]]".format(self))
            self._assign_cards()
            gevent.sleep(Game.WAIT_AFTER_CARDS_ASSIGNMENT)

            # Opening bet round
            self._logger.info("{}: [[first bet round]]".format(self))
            self._bet_round(bets=dict(self._bets))
            gevent.sleep(Game.WAIT_AFTER_BET)

            self._logger.info("{}: [[flop]]".format(self))
            self._shared_cards += self._deck.get_cards(3)
            self._evaluate_scores()
            self._bet_round()
            gevent.sleep(Game.WAIT_AFTER_BET)

            self._logger.info("{}: [[turn]]".format(self))
            self._shared_cards += self._deck.get_cards(1)
            self._evaluate_scores()
            self._bet_round()
            gevent.sleep(Game.WAIT_AFTER_BET)

            self._logger.info("{}: [[river]]".format(self))
            self._shared_cards += self._deck.get_cards(1)
            self._evaluate_scores()
            self._bet_round()
            gevent.sleep(Game.WAIT_AFTER_BET)

            # Winner detection
            self._logger.info("{}: [[winner detection]]".format(self))
            self._detect_winner()

        except EndGameException as e:
            pass