from poker import PlayerServer, JsonSocket, ScoreDetector, Deck, Game
import socket


if __name__ == '__main__':
    server_address = ('localhost', 9000)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(server_address)
    sock.listen(1)

    print("Poker server listening {}".format(str(server_address)))

    players = []

    try:
        room_size = 2
        stakes = 10.0

        while len(players) < room_size:
            client, address = sock.accept()
            print("New connection from {}".format(address))
            # Initializing the player
            player = PlayerServer(JsonSocket(client))
            players.append(player)
            print("Player {} '{}' CONNECTED".format(player.get_id(), player.get_name()))

        abort_game = False
        game = Game(players, Deck(lowest_rank=7), ScoreDetector(lowest_rank=7), stake=10.0)

        while not abort_game:
            game.play_hand()

            players_in_error = game.get_players_in_error()

            if players_in_error:
                for player in players_in_error:
                    if not player.try_resume():
                        player.disconnect()
                        abort_game = True

    finally:
        for player in players:
            player.disconnect()
