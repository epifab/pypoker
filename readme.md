# PyPoker

Traditional italian poker game application (5 card draw variant: https://en.wikipedia.org/wiki/Five-card_draw).

The backend is entirely written in Python and it uses flask microframework to handle web requests and web sockets.
The front-end is pure HTML/CSS/Javascript (jQuery).

### The game

When new players connect they automatically enter a game room.
As soon as a game room has at least two players seated, a new game is kicked off.

During a game session, players can leave and join active game rooms.

A live demo of this application can be found at: https://pypoker.herokuapp.com

![image](https://cloud.githubusercontent.com/assets/3248824/19188689/4ed266d2-8c8b-11e6-859d-124b829cd3b8.png)


### Architecture

The application is made of four components.
- **Game service**:
    - Background process responsible for launching new games. When new clients connect, they are moved to a "lobby". As soon as enough clients are waiting in the lobby, a new game is kicked off.
- **Backend web application**:
    - Handles HTTP requests and communicates to the clients via a persisted connection (web sockets).
    - Acts as a middle layer between the game service and the frontend web application.
- **Frontend web application**:
    - Handles any end user interactions.
- **Message broker**:
    - The backend web application and the game service communicate by pushing and pulling messages to and from a queue. This is done using Redis.


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
- *set-cards*
- *bet*
- *change-cards*
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

*game-update* message structure:

- *game_id* (id of the current game)
- *player_ids* (list of player ids)
- *players* (dictionary of players indexed by player ids). Every element of the list includes:
    -  *id*
    -  *name*
    -  *money*
    -  *bet* (total bet for the current hand)
    -  *alive* (true if the player has fold)
    -  *score* (this is sent only when the hand terminates and only for players who need to show their cards, see set-cards message for the structure)
- *pot*
- *dealer_id*
- *event* (see below)

The following is a list of possible events with their additional message attributes:

- **new-game** (a new game starts)
- **game-over** (current game was terminated)
- **cards-assignment** (cards have been assigned to every player)
- **player-action** (player action is required)
    - *player_id* (player asked to perform the given action)
    - *action* (either "change-cards" or "bet")
    - *timeout* (number of seconds allowed to respond)
    - *timeout_date* (timeout timestamp)
    - *min_bet* (only when *action* is "bet")
    - *max_bet* (only when *action* is "bet")
    - *opening* (only when *action* is "bet", true if nobody has bet in the current hand)
- **dead-player** (a player left the table)
    - *player_id* (dead player id)
- **bet** (a player bet)
    - *player_id* (player who bet)
    - *bet* (the actual bet. -1 if the player folded)
    - *bet_type* (either "call", "check", "open", "raise" or "fold")
- **cards-change** (a player changed the cards)
    - *player_id* (player who changed his cards)
    - *num_cards* (number of cards that were changed)
- **dead-hand** (hand terminated as nobody could open)
- **winner-designation**
    - *player* (zero-based index of the *players* list)

In addition to *game-update* messages, there are also some special messages which are exchanged directly with a particular client (while game-update messages are sent to every client)
There are also some private messages exchanged from the server with a specific client

- **set-card** (the server sends a list of cards to the client)
    - *score*:
        -  *cards* (list of cards)
            - every card on the list is a 2 elements integer list:
                - First element is the rank (14 = A, 13 = K, ...)
                - Second element is the suit (0 = spades, 1 = clubs, 2 = diamonds, 3 = hearts)
        -  *category*
            -  0: Highest card
            -  1: Pair
            -  2: Double pair
            -  3: Three of a kind
            -  4: Straight
            -  5: Full house
            -  6: Flush (note that flush is stronger than full house in traditional poker)
            -  7: Four of a kind
            -  8: Straight flush
- **change-cards** (sent by the client to the server)
    - *cards* (list of integers - arranging from 0 to 4):
        - every item in this list has to be a valid zero-based index of the *cards* list -- previously to the client sent via a *set-cards* message)
        - up to 4 cards can be changed
- **bet** (sent by the client)
    - *bet* (floating point. -1 to fold)

In the following example a player named "Jack" changes 4 cards (first, third, fourth and fifth cards in his hand):

```
{ 
    "message_type": "change-cards",
    "cards": [0, 2, 3, 4]
}
```

Being incredibly lucky, Jack gets back a crazy score from the server (4 of a kind!):

```
{ 
    "message_type": "set-cards",
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
    "event": "change-cards",
    "cards": 4,
    "player_id": "abcde-fghij-klmno-12345-2",
    "players": {
        "abcde-fghij-klmno-12345-1": {"id": "abcde-fghij-klmno-12345-1", "name": "John", "money": 123.0, "alive": true, "bet": 10.0}
        "abcde-fghij-klmno-12345-2": {"id": "abcde-fghij-klmno-12345-2", "name": "Jack", "money": 50.0, "alive": true, "bet": 10.0}
        "abcde-fghij-klmno-12345-3": {"id": "abcde-fghij-klmno-12345-3", "name": "Jeff", "money": 150.0, "alive": true, "bet": 10.0}
        "abcde-fghij-klmno-12345-4": {"id": "abcde-fghij-klmno-12345-4", "name": "Jane", "money": 500.0, "alive": true, "bet": 10.0}
    },
    "pot": 50.0,
    "dealer_id": "abcde-fghij-klmno-12345-4"
}
```

And shortly after a second *game-update* message to notify it's "Jack" turn to bet:

```
{ 
    "message_type": "game-update",
    "event": "player-action",
    "player_id": abcde-fghij-klmno-12345-2,
    "timeout": 30,
    "timeout_date": "2016-05-06 15:30:00+0000",
    "action": "bet",
    "min_bet": 1.0,
    "max_bet": 50.0,
    "players": ...
    "pot": 50.0,
    "dealer_id": "abcde-fghij-klmno-12345-4"
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

