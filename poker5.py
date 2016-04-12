import os
import gevent
from flask import Flask, render_template
from flask_sockets import Sockets
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = '!!_-pyp0k3r-_!!'
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
    "George",
]

surnames = [
    "Epiphan",
    "Morrison",
    "Handrix",
    "Lennon",
    "McCarty",
    "Harrison"
]

@app.route('/')
def hello():
    global names, surnames
    name = random.choice(names) + " " + random.choice(surnames)
    return render_template('index.html', name=name)


@sockets.route('/connect')
def connect(json):
    pass


@sockets.route('/disconnect')
def disconnect(json):
    pass


@sockets.route('/bet')
def bet(json):
    pass


@sockets.route('/discard-cards')
def discard_cards(json):
    pass



if __name__ == '__main__':
    app.run()