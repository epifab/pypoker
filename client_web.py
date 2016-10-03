import gevent
from flask import Flask, render_template, redirect, session, request, url_for
from flask_sockets import Sockets
from flask_oauthlib.client import OAuth, OAuthException
import redis
import uuid
import os
import time
from poker import PlayerClient, ChannelWebSocket, ChannelRedis, \
    MessageQueue, ChannelError, MessageFormatError, MessageTimeout


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
    if "oauth-token" not in session:
        return redirect(url_for("login"))

    user = facebook.get("/me?fields=name,email")

    session["player-id"] = user.data["id"]
    session["player-name"] = user.data["name"]
    session["player-money"] = 1000

    return render_template("index.html",
                           id=session["player-id"],
                           name=session["player-name"],
                           money=session["player-money"])


@app.route("/login")
def login():
    callback = url_for(
        "facebook_authorized",
        next=request.args.get("next") or request.referrer or None,
        _external=True
    )
    return facebook.authorize(callback=callback)


@app.route("/login/authorized")
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
    return redirect("/")


@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get("oauth-token")


@sockets.route("/poker5")
def poker5(ws):
    client_channel = ChannelWebSocket(ws)

    if "player-id" not in session:
        client_channel.send_message({"msg_id": "error", "error": "Unrecognized user"})
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

    player = PlayerClient(
        server_channel=server_channel,
        client_channel=client_channel,
        id=player_id,
        name=player_name,
        money=player_money,
        logger=app.logger
    )

    try:
        app.logger.info("Connecting player {} to a poker5 server...".format(player_id))
        player.connect(MessageQueue(redis), session_id)
    except (ChannelError, MessageFormatError, MessageTimeout) as e:
        app.logger.error("Unable to connect player {} to a poker5 server: {}".format(player_id, e.args[0]))
        raise

    def keep_alive():
        last_ping = time.time()
        while not ws.closed:
            # Keep the websocket alive
            gevent.sleep(0.1)
            if time.time() > last_ping + 20:
                # Ping the client every 20 secs to prevent idle connections
                player.send_message_client({"msg_id": "keep_alive"})
                last_ping = time.time()

    try:
        # Keep websocket open
        gevent.spawn(keep_alive)
        player.play()
    except (ChannelError, MessageFormatError, MessageTimeout) as e:
        app.logger.error("Terminating player {} connection: {}".format(player_id, e.args[0]))
    finally:
        app.logger.info("Dropping connection with {}".format(player))
        player.disconnect()
