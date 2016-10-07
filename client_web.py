import gevent
from flask import Flask, render_template, redirect, session, request, url_for
from flask_sockets import Sockets
from flask_oauthlib.client import OAuth, OAuthException
import random
import redis
import uuid
import os
import time
from poker import ChannelWebSocket, ChannelRedis, MessageQueue, ChannelError, MessageFormatError, MessageTimeout


app = Flask(__name__)
app.config["SECRET_KEY"] = "!!_-pyp0k3r-_!!"
app.debug = True

sockets = Sockets(app)
oauth = OAuth(app)

redis_url = os.environ["REDIS_URL"]
redis = redis.from_url(redis_url)

facebook = oauth.remote_app(
    "facebook",
    consumer_key=os.environ["FACEBOOK_APP_ID"],
    consumer_secret=os.environ["FACEBOOK_APP_SECRET"],
    request_token_params={"scope": "email"},
    base_url="https://graph.facebook.com",
    request_token_url=None,
    access_token_url="/oauth/access_token",
    access_token_method="GET",
    authorize_url="https://www.facebook.com/dialog/oauth"
)


@app.route("/")
def index():
    if "player-id" not in session:
        return render_template("index.html", template="login.html")

    return render_template("index.html",
                           template="game.html",
                           player_id=session["player-id"],
                           player_name=session["player-name"],
                           player_money=session["player-money"])


@app.route("/test-login")
def test_login():
    session["player-id"] = str(uuid.uuid4())
    session["player-name"] = get_random_name()
    session["player-money"] = 1000
    return redirect(url_for("index"))


@app.route("/facebook-login")
def login():
    callback = url_for(
        "facebook_authorized",
        next=request.args.get("next") or request.referrer or None,
        _external=True
    )
    return facebook.authorize(callback=callback)


@app.route("/facebook-login/authorized")
def facebook_authorized():
    response = facebook.authorized_response()

    if response is None:
        return "Access denied: reason={} error={}".format(
            request.args["error_reason"],
            request.args["error_description"]
        )

    if isinstance(response, OAuthException):
        return "Access denied: {}".format(response.message)

    session["oauth-token"] = (response["access_token"], "")

    user = facebook.get("/me?fields=name,email")

    session["player-id"] = user.data["id"]
    session["player-name"] = user.data["name"]
    session["player-money"] = 1000

    return redirect(url_for("index"))


@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get("oauth-token")


@sockets.route("/poker5")
def poker5(ws):
    client_channel = ChannelWebSocket(ws)

    if "player-id" not in session:
        client_channel.send_message({"message_type": "error", "error": "Unrecognized user"})
        client_channel.close()
        return

    session_id = str(uuid.uuid4())

    player_id = session["player-id"]
    player_name = session["player-name"]
    player_money = session["player-money"]

    server_channel = ChannelRedis(
        redis,
        "poker5:player-{}:session-{}:O".format(player_id, session_id),
        "poker5:player-{}:session-{}:I".format(player_id, session_id)
    )

    try:
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #  Player connection
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        app.logger.info("Connecting player {} to a poker5 server...".format(player_id))

        message_queue = MessageQueue(redis)

        message_queue.push(
            "poker5:lobby",
            {
                "message_type": "connect",
                "player": {
                    "id": player_id,
                    "name": player_name,
                    "money": player_money
                },
                "session_id": session_id
            }
        )

        connection_message = server_channel.recv_message(time.time() + 5)  # 5 seconds

        # Validating message id
        MessageFormatError.validate_message_type(connection_message, "connect")

        server_id = str(connection_message["server_id"])

        app.logger.info("player {}: connected to server {}".format(player_id, server_id))

        # Forwarding connection message to the client
        client_channel.send_message(connection_message)

    except (ChannelError, MessageFormatError, MessageTimeout) as e:
        app.logger.error("Unable to connect player {} to a poker5 server: {}".format(player_id, e.args[0]))

    else:
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


def get_random_name():
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
    return random.choice(names)
