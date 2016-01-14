from poker import PlayerServer, JsonSocket, ScoreDetector, Deck, Game
import socket

if __name__ == '__main__':
    server_address = ('localhost', 9000)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(server_address)
    sock.listen(1)

    print("Poker server listening {}".format(str(server_address)))

    clients = []
    players = []

    try:
        while len(clients) != 2:
            client, address = sock.accept()
            clients.append(client)
            print("New connection from {}".format(address))
            player = PlayerServer(JsonSocket(client))
            players.append(player)
            print("Player '{}' ${:,.2f} CONNECTED".format(player.get_name(), player.get_money()))

        print("Starting a new game")
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

    finally:
        for client in clients:
            client.close()