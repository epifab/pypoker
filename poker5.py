import os
import gevent
from flask import Flask, render_template, session
from flask_sockets import Sockets
import random
import uuid
import time
from poker import ServerWebSocket, WebSocketChannel, PlayerServer

app = Flask(__name__)
app.config['SECRET_KEY'] = '!!_-pyp0k3r-_!!'
app.debug = True

sockets = Sockets(app)

server = ServerWebSocket(app.logger)
gevent.spawn(server.start)

# Poker champions: https://en.wikipedia.org/wiki/List_of_World_Series_of_Poker_Main_Event_champions
names = [
    "Johnny Moss",
    "Thomas Preston",
    "Walter Pearson",
    "Brian Roberts",
    "Doyle Brunson",
    "Bobby Baldwin",
    "Hal Fowler",
    "Stu Ungar",
    "Jack Straus",
    "Tom McEvoy",
    "Jack Keller",
    "Bill Smith",
    "Barry Johnston",
    "Johnny Chan",
    "Phil Hellmuth",
    "Mansour Matloubi",
    "Brad Daugherty",
    "Hamid Dastmalchi",
    "Jim Bechtel",
    "Russ Hamilton",
    "Dan Harrington",
    "Huck Seed",
    "Stu Ungar",
    "Scotty Nguyen",
    "Noel Furlong",
    "Chris Ferguson",
    "Carlos Mortensen",
    "Robert Varkonyi",
    "Chris Moneymaker",
    "Greg Raymer",
    "Joe Hachem",
    "Jamie Gold",
    "Jerry Yang",
    "Peter Eastgate",
    "Joe Cada",
    "Jonathan Duhamel",
    "Pius Heinz",
    "Greg Merson",
    "Ryan Riess",
    "Martin Jacobson",
    "Joe McKeehen",
]

players = {}


@app.route('/')
def hello():
    global names
    if 'player-id' not in session:
        session['player-id'] = str(uuid.uuid4())
        session['player-name'] = random.choice(names)
        session['player-money'] = 1000.00
    return render_template('index.html',
                           id=session['player-id'],
                           name=session['player-name'],
                           money=session['player-money'])


@sockets.route('/poker5')
def poker5(ws):
    player = PlayerServer(
        channel=WebSocketChannel(ws),
        id=session['player-id'],
        name=session['player-name'],
        money=session['player-money'])

    server.register(player)

    last_ping = time.time()
    while not ws.closed:
        # Keep the websocket alive
        gevent.sleep(0.1)
        if time.time() > last_ping + 20:
            # Ping the client every 20 secs to prevent idle connections
            player.ping()
            last_ping = time.time()
    app.logger.info("Dropping connection with {}".format(player))


if __name__ == '__main__':
    app.run()
