import os
import gevent
from flask import Flask, render_template, session
from flask_sockets import Sockets
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = '!!_-pyp0k3r-_!!'
app.debug = True

sockets = Sockets(app)

names = [
    "Leonard",
    "Michael",
    "Fab",
    "Charles",
    "Jim",
    "Jimy",
    "John",
    "Paul",
    "George",]

surnames = [
    "Morrison",
    "Hendrix",
    "Lennon",
    "McCartney",
    "Harrison",]


@app.route('/')
def hello():
    global names, surnames
    if 'player-name' not in session:
        session['player-name'] = random.choice(names) + " " + random.choice(surnames)
        session['player-money'] = 1000.00
    return render_template('index.html', name=session['player-name'], money=session['player-money'])


@sockets.route('/poker5')
def poker5(ws):
    """Receives incoming chat messages, inserts them into Redis."""
    while not ws.closed:
        # Sleep to prevent *constant* context-switches.
        gevent.sleep(0.1)
        message = ws.receive()

        if message:
            app.logger.info(u'Inserting message: {}'.format(message))

ok