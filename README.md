# PyPoker

Poker game application built for fun.

It supports different poker games (currently texas holdem and traditional 5 card draw).
The backend is entirely written in Python and it uses flask microframework to handle web requests and web sockets.
The front-end is pure HTML/CSS/Javascript (jQuery).

### The game

When new players connect they automatically enter a game room.
As soon as a game room has at least two players seated, a new game is kicked off.

During a game session, other players can leave and join the table.

A live demo of this application can be found at: https://pypoker.herokuapp.com

![image](https://cloud.githubusercontent.com/assets/3248824/19602814/950fcbd2-97a6-11e6-9e9d-faabeac2307f.png)


### Architecture

The application is made of four components.
- **Game service**:
    - Background process responsible for launching new games.
    - There are currently two game services (texasholdem_poker_service.py and traditional_poker_service.py).
- **Backend web application**:
    - Handles HTTP requests and communicates to the clients via a persisted connection (web sockets).
    - Acts as a middle layer between the game service and the frontend web application.
- **Frontend web application**:
    - Handles any end user interactions.
- **Message broker**:
    - The backend web application and the game services communicate by pushing and pulling messages to and from a queue. This is done using Redis.


Note: even if they are in the same repository, the game service and the web application are completely decoupled.
They can be deployed on different servers and scaled independently as the communication only happens by exchanging JSON messages via a distributed database.


### Communication protocol

As mentioned above, front-end clients communicate to the backend application by exchanging JSON messages over a persisted HTTP connection using web sockets.

A working example of a client application can be found under: static/js/application.js

Every message will contain a self-explanatory field named **message_type**.

There are 8 possible message types:
- *connect*
- *disconnect*
- *room-update*
- *game-update*
- *bet*
- *cards-change*
- *error*


#### Connection

When a player connects, he receives a connection message:

```
{
    "message_type": "connect",
    "server_id": "vegas123",
    "player": {"id": "abcde-fghij-klmno-12345-1", "name": "John", "money": 1000.0}
}
```

Unless catastrophic crashes, every poker session is terminated by receiving (or sending) a *disconnect* message_type.

```
{"message_type": "disconnect"}
```


#### Room updates

Shortly after the connection, the player automatically lands in a poker room and starts receiving **room-update** messages describing any room related event.

There are three possible *room-update* events:
- **init**: this is sent straight after the player joined a game room
- **player-added**: sent any time a new player joins the game room
- **player-removed**: sent any time a player leaves the game room

```
{
    "message_type": "room-update",
    "event": "init",
    "room_id": "vegas123/345",
    "player_ids": [
        "abcde-fghij-klmno-12345-1",
        "abcde-fghij-klmno-12345-2",
        null,
        null
    ],
    "players": {
        "abcde-fghij-klmno-12345-1": {
            "id": "abcde-fghij-klmno-12345-1",
            "name": "John",
            "money": 123.0,
        }
        "abcde-fghij-klmno-12345-2": {
            "id": "abcde-fghij-klmno-12345-2",
            "name": "Jack",
            "money": 50.0
        }
    }
}
```


```
{
    "message_type": "room-update",
    "event": "player-added",
    "room_id": "vegas123/345",
    "player_id": "abcde-fghij-klmno-12345-3"
    "player_ids": [
        "abcde-fghij-klmno-12345-1",
        "abcde-fghij-klmno-12345-2",
        "abcde-fghij-klmno-12345-3",
        null
    ],
    "players": {
        ...
    }
}
```


```
{
    "message_type": "room-update",
    "event": "player-removed",
    "room_id": "vegas123/345",
    "player_id": "abcde-fghij-klmno-12345-2"
    "player_ids": [
        "abcde-fghij-klmno-12345-1",
        null,
        "abcde-fghij-klmno-12345-3",
        null
    ],
    "players": {
        ...
    }
}
```


#### Game updates

Once there are at least two players in the room a new game is automatically launched. 
At this point, the remote server starts broadcasting **game-update** messages to communicate every game related event to the frontend clients (for instance "player X bet 100 dollars", "player Y changed 3 cards", "player Z won", ...).

Frontend clients will respond to particular messages which indicate that input is required from the end users (for instance a bet or which cards they wish the change).

*game-update* messages structure depend on the specific event that generate them.

Here's a list of possible events:

- **new-game** (a new game starts)
- **game-over** (current game was terminated)
- **cards-assignment** (cards assigned to each player)
- **player-action** (player action is required)
- **cards-change** (a player changed some cards - only for traditional poker games)
- **bet** (a player check, call or raise)
- **fold** (a player fold)
- **dead-player** (a player left the table)
- **showdown** (active players showdown their cards)
- **pots-update** (when money go to the pots)
- **winner-designation** (winner designation for each pot)

The client communicate player decisions via two message types:

- **cards-change** (containing the list of cards the player wish to change - only for traditional poker games)
- **bet** (the actual bet)

In the following example a player named "Jack" changes 4 cards (first, third, fourth and fifth cards in his hand):

```
{ 
    "message_type": "cards-change",
    "cards": [0, 2, 3, 4]
}
```

Being incredibly lucky, Jack gets back a crazy score from the server (4 of a kind!):

```
{ 
    "message_type": "cards-assignment",
    "cards": [[14, 3], [14, 2], [14, 1], [14, 0], [9, 3]],
    "score": {
        "cards": [[14, 3], [14, 2], [14, 1], [14, 0], [9, 3]],
        "category": 7
    }
}
```

At this point, the server sends a first *game-update* message to notify that Jack changed 4 cards:

```
{ 
    "message_type": "game-update",
    "event": "cards-change",
    "num_cards": 4,
    "player": {
        "id": "abcde-fghij-klmno-12345-2",
        "name": "Jack",
        "money": 50.0
    }
}
```

And shortly after a second *game-update* message to notify it's "Jack" turn to bet:

```
{ 
    "message_type": "game-update",
    "event": "player-action",
    "player": {
        "id": "abcde-fghij-klmno-12345-2",
        "name": "Jack",
        "money": 50.0
    }
    "timeout": 30,
    "timeout_date": "2016-05-06 15:30:00+0000",
    "action": "bet",
    "min_bet": 1.0,
    "max_bet": 50.0,
}
```

At this point Jack goes all in:

```
{ 
    "message_type": "bet",
    "bet": 50.0
}
```

The server broadcasts 2 new messages to notify that Jack raised to $50.0 and that it's now Jeff's turn to bet, who wisely decides to fold...

