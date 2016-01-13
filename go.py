from poker import Deck, ScoreDetector, PlayerConsole, Player
from poker.game import Game

score_detector = ScoreDetector(7)
deck = Deck(7)
players = [PlayerConsole("Player 1", 1000, score_detector),
           PlayerConsole("Player 2", 1000, score_detector),
           PlayerConsole("Player 3", 1000, score_detector),
           PlayerConsole("Player 4", 1000, score_detector)]
g = Game(players, deck, score_detector, 10.0)
g.play_game()
