import os
import uuid

import gevent
import redis
from flask import Flask, render_template, redirect, session, url_for, request
from flask_sockets import Sockets

from poker.channel import ChannelError, MessageFormatError, MessageTimeout
from poker.channel_websocket import ChannelWebSocket
from poker.player import Player
from poker.player_client import PlayerClientConnector

app = Flask(__name__)
app.config["SECRET_KEY"] = "!!_-pyp0k3r-_!!"
app.debug = True

sockets = Sockets(app)

redis_url = os.environ["REDIS_URL"]
redis = redis.from_url(redis_url)


@app.route("/")
def index():
    if "player-id" not in session:
        return render_template("index.html", template="login.html")

    return render_template("index.html",
                           template="game.html",
                           player_id=session["player-id"],
                           player_name=session["player-name"],
                           player_money=session["player-money"])


@app.route("/join", methods=["POST"])
def join():
    name = request.form["name"]
    room_id = request.form["room-id"]
    session["player-id"] = str(uuid.uuid4())
    session["player-name"] = name
    session["player-money"] = 1000
    session["room-id"] = room_id if room_id else None
    return redirect(url_for("index"))


@sockets.route("/poker/texas-holdem")
def texasholdem_poker_game(ws):
    return poker_game(ws, "texas-holdem-poker:lobby")


@sockets.route("/poker/traditional")
def traditional_poker_game(ws):
    return poker_game(ws, "traditional-poker:lobby")


def poker_game(ws, connection_channel):
    client_channel = ChannelWebSocket(ws)

    if "player-id" not in session:
        client_channel.send_message({"message_type": "error", "error": "Unrecognized user"})
        client_channel.close()
        return

    session_id = str(uuid.uuid4())

    player_id = session["player-id"]
    player_name = session["player-name"]
    player_money = session["player-money"]
    room_id = session["room-id"]

    player_connector = PlayerClientConnector(redis, connection_channel, app.logger)

    try:
        server_channel = player_connector.connect(
            player=Player(
                id=player_id,
                name=player_name,
                money=player_money
            ),
            session_id=session_id,
            room_id=room_id
        )

    except (ChannelError, MessageFormatError, MessageTimeout) as e:
        app.logger.error("Unable to connect player {} to a poker5 server: {}".format(player_id, e.args[0]))

    else:
        # Forwarding connection to the client
        client_channel.send_message(server_channel.connection_message)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #  Game service communication
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        def message_handler(channel1, channel2):
            # Forward messages received from channel1 to channel2
            try:
                while True:
                    message = channel1.recv_message()
                    if "message_type" in message and message["message_type"] == "disconnect":
                        raise ChannelError
                    channel2.send_message(message)
            except (ChannelError, MessageFormatError):
                pass

        greenlets = [
            # Forward client messages to the game service
            gevent.spawn(message_handler, client_channel, server_channel),
            # Forward game service messages to the client
            gevent.spawn(message_handler, server_channel, client_channel)
        ]

        def closing_handler(*args, **kwargs):
            # Kill other active greenlets
            gevent.killall(greenlets, ChannelError)

        greenlets[0].link(closing_handler)
        greenlets[1].link(closing_handler)

        gevent.joinall(greenlets)

        try:
            client_channel.send_message({"message_type": "disconnect"})
        except:
            pass
        finally:
            client_channel.close()

        try:
            server_channel.send_message({"message_type": "disconnect"})
        except:
            pass
        finally:
            server_channel.close()

        app.logger.info("player {} connection closed".format(player_id))
