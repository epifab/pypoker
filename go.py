from poker import Deck, ScoreDetector, PlayerConsole, Player
from poker.game import Game

players = [
    PlayerConsole("Player 1", 1000),
    PlayerConsole("Player 2", 1000),
    PlayerConsole("Player 3", 1000),
    PlayerConsole("Player 4", 1000),]

game = Game(players, Deck(lowest_rank=7), ScoreDetector(lowest_rank=7), stake=10.0)

game.play_hand()
while True:
    print()
    yes_no = input("Another hand? (Y/N) ")
    if yes_no.upper() == 'Y':
        game.play_hand()
        continue
    elif yes_no.upper() == 'N':
        break
