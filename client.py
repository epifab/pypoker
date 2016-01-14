from poker import JsonSocket, PlayerClientConsole, Card, Score
import socket, sys

if __name__ == '__main__':
    name = sys.argv[1]

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 9000))

    player = PlayerClientConsole(JsonSocket(sock), name=name, money=1000)

    print("Player '{}' ${:,.2f} CONNECTED".format(player.get_name(), player.get_money()))

    try:
        while True:
            message = player.recv_message()

            if message['msg_id'] == 'game-update':
                str(message)

            elif message['msg_id'] == 'bet':
                player.bet(min_bet=message['min_bet'], max_bet=message['max_bet'], opening=message['opening'])

            elif message['msg_id'] == 'set-cards':
                player.set_cards(
                    [Card(rank, suit) for rank, suit in message['cards']],
                    Score(message['score']['category'], [Card(rank, suit) for rank, suit in message['score']['cards']])
                )

            elif message['msg_id'] == 'discard-cards':
                player.discard_cards()
    finally:
        sock.close()