from poker import JsonSocket, PlayerClientConsole, Card, Score, Game
import socket
import sys


def print_game_update(message, player):
    print()
    print("~" * 45)

    if message['phase'] == Game.PHASE_CARDS_ASSIGNMENT:
        for p2 in message['players']:
            print("Player '{}'\n Cash: ${:,.2f}\n Bets: ${:,.2f}".format(
                p2['name'],
                p2['money'],
                p2['bet']))

            if p2['id'] == player.get_id():
                print(Card.format_cards(player.get_score().get_cards()))
                player.set_money(p2['money'])
            else:
                print("+-------+" * 5)
                print("| ///// |" * 5)
                print("| ///// |" * 5)
                print("| ///// |" * 5)
                print("| ///// |" * 5)
                print("| ///// |" * 5)
                print("+-------+" * 5)

    elif message['phase'] == Game.PHASE_OPENING_BET or message['phase'] == Game.PHASE_FINAL_BET:
        pname = message['players'][message['player']]['name']
        if message['bet_type'] == 'RAISE':
            print("Player '{}' bet ${:,.2f} RAISE".format(pname, message['bet'], message['bet_type']))
        else:
            print("Player '{}' {}".format(pname, message['bet_type']))

    elif message['phase'] == Game.PHASE_CARDS_CHANGE:
        pname = message['players'][message['player']]['name']
        print("Player '{}' changed {} cards".format(pname, message['num_cards']))

    elif message['phase'] == Game.PHASE_SHOW_CARDS:
        pname = message['players'][message['player']]['name']
        if not message['score']:
            print("Player '{}' FOLD".format(pname))
        else:
            score = Score(
                message['score']['category'],
                [Card(rank, suit) for (rank, suit) in message['score']['cards']])
            print("Player '{}' score:".format(pname))
            print(str(score))

    elif message['phase'] == Game.PHASE_WINNER_DESIGNATION:
        pname = message['players'][message['player']]['name']
        print()
        print("~" * 45)
        print("Player '{}' WON!!!".format(pname))
        print("~" * 45)
        print()

    print()
    print("Pot: ${:,.2f}".format(message['pot']))
    print("~" * 45)
    print()
    print("Waiting...")


if __name__ == '__main__':
    name = sys.argv[1]

    server_address = ('localhost', 9000)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)

    player = PlayerClientConsole(JsonSocket(socket=sock, address=server_address), name=name, money=1000)

    print("Player '{}' ${:,.2f} CONNECTED".format(player.get_name(), player.get_money()))

    try:
        while True:
            message = player.recv_message()

            if message['msg_id'] == 'game-update':
                print_game_update(message, player)

            elif message['msg_id'] == 'bet':
                player.bet(min_bet=message['min_bet'], max_bet=message['max_bet'], opening=message['opening'])

            elif message['msg_id'] == 'set-cards':
                player.set_cards(
                    [Card(rank, suit) for rank, suit in message['cards']],
                    Score(message['score']['category'], [Card(rank, suit) for rank, suit in message['score']['cards']]))

            elif message['msg_id'] == 'discard-cards':
                player.discard_cards()

    finally:
        sock.close()
