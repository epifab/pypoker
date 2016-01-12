from poker.deck import Deck
from poker.player_console import PlayerConsole
from poker.score_detector import ScoreDetector
from poker.game import Game


score_detector = ScoreDetector(7)
deck = Deck(7)
players = [PlayerConsole(1, "Player 1", 1000, score_detector),
           PlayerConsole(2, "Player 2", 1000, score_detector),
           PlayerConsole(3, "Player 3", 1000, score_detector),
           PlayerConsole(4, "Player 4", 1000, score_detector)]
g = Game(players, deck, score_detector, 10.0)
g.play_game()
