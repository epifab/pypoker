from poker.deck import Deck
from poker.console_player import ConsolePlayer
from poker.score_detector import ScoreDetector
from poker.game import Game


score_detector = ScoreDetector(7)
deck = Deck(7)
players = [ConsolePlayer(1, "Player 1", 1000, score_detector),
           ConsolePlayer(2, "Player 2", 1000, score_detector),
           ConsolePlayer(3, "Player 3", 1000, score_detector),
           ConsolePlayer(4, "Player 4", 1000, score_detector)]
g = Game(players, deck, score_detector, 10.0)
g.play_game()
