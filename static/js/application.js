Poker5 = {
    socket: null,

    betMode: false,

    cardsChangeMode: true,

    roomId: null,

    gameId: null,

    scoreCategories: {
        0: "Highest card",
        1: "Pair",
        2: "Double pair",
        3: "Three of a kind",
        4: "Straight",
        5: "Full house",
        6: "Flush",
        7: "Four of a kind",
        8: "Straight flush"
    },

    log: function(text) {
        $p0 = $('#game-status p[data-key="0"]');
        $p1 = $('#game-status p[data-key="1"]');
        $p2 = $('#game-status p[data-key="2"]');
        $p3 = $('#game-status p[data-key="3"]');
        $p4 = $('#game-status p[data-key="4"]');

        $p4.text($p3.text());
        $p3.text($p2.text());
        $p2.text($p1.text());
        $p1.text($p0.text());
        $p0.text(text);
    },

    init: function() {
        wsScheme = window.location.protocol == "https:" ? "wss://" : "ws://";

        this.socket = new WebSocket(wsScheme + location.host + "/poker5");

        this.socket.onopen = function() {
            Poker5.log('Connected :)');
        };

        this.socket.onclose = function() {
            Poker5.log('Disconnected :(');
        };

        this.socket.onmessage = function(message) {
            var data = JSON.parse(message.data);

            console.log(data);

            switch (data.msg_id) {
                case 'ping':
                    Poker5.socket.send(JSON.stringify({'msg_id': 'pong'}));
                    break;
                case 'connect':
                    Poker5.onConnect(data);
                    break;
                case 'disconnect':
                    Poker5.onDisconnect(data);
                    break;
                case 'room-update':
                    Poker5.onRoomUpdate(data);
                    break;
                case 'set-cards':
                    Poker5.onSetCards(data);
                    break;
                case 'game-update':
                    Poker5.onGameUpdate(data);
                    break;
                case 'error':
                    Poker5.log('Error received: ' + data.error);
                    break;
                case 'timeout':
                    Poker5.log('Timed out');
                    break;
            }
        };

        $('#current-player .card').click(function() {
            if (Poker5.cardsChangeMode) {
                $(this).toggleClass('selected');
            }
        });

        $('#change-cards-cmd').click(function() {
            discards = [];
            $('#current-player .card.selected').each(function() {
                discards.push($(this).data('key'))
            });
            Poker5.socket.send(JSON.stringify({
                'msg_id': 'change-cards',
                'cards': discards
            }));
            Poker5.setCardsChangeMode(false);
        });

        $('#fold-cmd, #no-bet-cmd').click(function() {
            Poker5.socket.send(JSON.stringify({
                'msg_id': 'bet',
                'bet': -1
            }));
            Poker5.disableBetMode();
        });

        $('#bet-cmd').click(function() {
            Poker5.socket.send(JSON.stringify({
                'msg_id': 'bet',
                'bet': $('#bet-input').val()
            }));
            Poker5.disableBetMode();
        });

        this.setCardsChangeMode(false);
        this.disableBetMode();
    },

    onGameUpdate: function(message) {
        if (message.event == 'game-over') {
            $('.player').removeClass('winner');
            $('.player').addClass('inactive');
            $('.player .bet').text('');
            $('#current-player').hide();
            this.gameId = null;
        }
        else {
            if (this.gameId == null) {
                this.resetCards();
                $('#current-player').show();
            }
            this.updateGame(message);
        }

        this.resetControls();
        this.resetTimers();

        switch (message.event) {
            case 'new-game':
                this.log('New game');
                break;
            case 'game-over':
                this.log('Game over');
                break;
            case 'cards-assignment':
                this.log('New hand');
                break;
            case 'bet':
                player = message.players[message.player_id];
                playerName = player.id == $('#current-player').data('id') ? 'You' : player.name;

                switch (message.bet_type) {
                    case 'fold':
                    case 'pass':
                    case 'check':
                        this.log(playerName + " " + message.bet_type);
                        break;
                    case 'open':
                    case 'call':
                    case 'raise':
                        this.log(playerName + " bet $" + parseInt(message.bet) + " (" + message.bet_type + ")");
                        break;
                }
                break;
            case 'cards-change':
                player = message.players[message.player_id];
                playerName = player.id == $('#current-player').data('id') ? 'You' : player.name;
                this.log(playerName + " changed " + message.num_cards + " cards.");
                break;
            case 'player-action':
                this.onPlayerAction(message);
                break;
            case 'dead-player':
                player = message.players[message.player_id];
                this.log(player.name + " left.")
                break;
            case 'winner-designation':
                player = message.players[message.player_id];
                playerName = player.id == $('#current-player').data('id') ? 'You' : player.name;
                this.log(playerName + " won!");
                break;
        }
    },

    onConnect: function(message) {
        this.log("Connection established with poker5 server: " + message.server_id);
        $('#current-player').data('id', message.player.id);
    },

    onDisconnect: function(message) {

    },

    onError: function(message) {
        Poker5.log('ERROR: ' + message.error);
    },

    onTimeout: function(message) {
        Poker5.log('Time is up!');
        Poker5.disableBetMode();
        Poker5.setCardsChangeMode(false);
    },

    createPlayer: function(player) {
        isCurrentPlayer = player.id == $('#current-player').data('id');

        $playerName = $('<p class="player-name"></p>');
        $playerName.text(isCurrentPlayer ? 'You' : player.name);

        $playerMoney = $('<p class="player-money"></p>');
        $playerMoney.text('$' + parseInt(player.money));

        $playerInfo = $('<div class="player-info"></div>');
        $playerInfo.append($playerName);
        $playerInfo.append($playerMoney);

        $player = $('<div class="player inactive' + (isCurrentPlayer ? ' current' : '') + '"></div>');
        $player.attr('data-id', player.id);
        $player.append($('<div class="cards"></div>'));
        $player.append($playerInfo);
        $player.append($('<div class="timer"></div>'));
        $player.append($('<div class="bet"></div>'));

        return $player;
    },

    onRoomUpdate: function(message) {
        if (message['event'] == 'init') {
            this.roomId = message.room_id;
            // Initializing the room
            $('#players').empty();
            for (k in message.player_ids) {
                $seat = $('<div class="seat"></div>');
                $seat.attr('data-key', k);

                playerId = message.player_ids[k];

                if (playerId) {
                    // This seat is taken
                    $seat.append(this.createPlayer(message.players[playerId]));
                }
                $('#players').append($seat);
            }
        }
        else {
            playerId = message.player_id;
            player = message.players[playerId]
            playerName = playerId == $('#current-player').data('id') ? 'You' : player.name;

            switch (message.event) {
                case 'player-added':
                    this.log(playerName + " joined");
                    for (k in message.player_ids) {
                        if (message.player_ids[k] == playerId) {
                            $seat = $('.seat[data-key="' + k + '"]');
                            $seat.empty();
                            $seat.append(this.createPlayer(player));
                            break;
                        }
                    }
                    break;

                case 'player-removed':
                    this.log(playerName + " left");
                    $('.player[data-id="' + playerId + '"]').remove();
                    break;
            }
        }
    },

    onSetCards: function(message) {
        for (cardKey in message.cards) {
            Poker5.setCard(
                cardKey,
                message.cards[cardKey][0],
                message.cards[cardKey][1]);
        }
        $('#current-player .cards .category').text(Poker5.scoreCategories[message.score.category]);
        $('#current-player').data('allowed-to-open', message.allowed_to_open);
    },

    onBet: function(message) {
        Poker5.enableBetMode(message);
        $("html, body").animate({ scrollTop: $(document).height() }, "slow");
    },

    onChangeCards: function(message) {
        this.setCardsChangeMode(true);
        $("html, body").animate({ scrollTop: $(document).height() }, "slow");
    },

    updateGame: function(message) {
        this.gameId = message.game_id;

        $('#pot').text(parseInt(message.pot));

        for (k in message.player_ids) {
            playerId = message.player_ids[k]
            player = message.players[playerId]

            $player = $('.player[data-id="' + player.id + '"]');

            $cards = $('#players .player[data-id="' + player.id + '"] .cards');
            $cards.empty();

            if (player.score) {
                for (cardKey in player.score.cards) {
                    card = player.score.cards[cardKey];

                    switch (card[0]) {
                        case 11:
                            rank = 'J';
                            break;
                        case 12:
                            rank = 'Q';
                            break;
                        case 13:
                            rank = 'K';
                            break;
                        case 1:
                        case 14:
                            rank = 'A';
                            break;
                        default:
                            rank = card[0];
                    }

                    switch (card[1]) {
                        case 3:
                            suit = "hearts";
                            break;
                        case 2:
                            suit = "diams";
                            break;
                        case 1:
                            suit = "clubs";
                            break;
                        default:
                            suit = "spades";
                            break;
                    }

                    $cards.append(
                        '<div class="card text" data-suit="' + suit + '">'
                        + '<div class="rank">' + rank + '</div>'
                        + '<div class="suit">&' + suit + ';</div>'
                        + '</div>'
                    );
                }

                $cards.append('<div class="category">' + Poker5.scoreCategories[player.score.category] + "</div>")
            }

            $('.player[data-id="' + player.id + '"] .player-money').text("$" + parseInt(player.money));
            $('.player[data-id="' + player.id + '"] .bet').text("$" + parseInt(player.bet));

            winner = message.event == 'winner-designation' && message.player_id == playerId;
            winner
                ? $player.addClass('winner')
                : $player.removeClass('winner');

            alive = player.alive && (message.event != 'winner-designation' || message.player_id == playerId);
            alive
                ? $player.removeClass('inactive')
                : $player.addClass('inactive');
        }
    },

    onPlayerAction: function(message) {
        player = message.players[message.player_id];
        isCurrentPlayer = player.id == $('#current-player').data('id');

        switch (message.action) {
            case 'bet':
                if (isCurrentPlayer) {
                    this.log('Your turn to bet');
                    this.onBet(message);
                }
                else {
                    this.log('Waiting for ' + player.name + ' to bet...');
                }
                break;
            case 'change-cards':
                if (isCurrentPlayer) {
                    this.log('Your turn to change cards');
                    this.onChangeCards(message);
                }
                else {
                    this.log('Waiting for ' + player.name + ' to change cards...');
                }
                break;
        }

        $timers = $('.player[data-id="' + player.id + '"] .timer');
        $timers.data('timer', message.timeout);
        $timers.TimeCircles({
            "start": true,
            "animation": "smooth",
            "bg_width": 1,
            "fg_width": 0.05,
            "count_past_zero": false,
            "time": {
                "Days": { show: false },
                "Hours": { show: false },
                "Minutes": { show: false },
                "Seconds": { show: true }
            }
        });
        $timers.addClass('active');
    },

    resetTimers: function() {
        // Reset timers
        $activeTimers = $('.timer.active');
        $activeTimers.TimeCircles().destroy();
        $activeTimers.removeClass('active');
    },

    resetControls: function() {
        // Reset controls
        this.setCardsChangeMode(false);
        this.disableBetMode();
    },

    sliderHandler: function(value) {
        if (value == 0) {
            $('#bet-cmd').attr("value", "Check");
        }
        else {
            $('#bet-cmd').attr("value", "$" + parseInt(value));
        }
        $('#bet-input').val(value);
    },

    enableBetMode: function(message) {
        this.betMode = true;

        if (!message.opening || $('#current-player').data('allowed-to-open')) {
            // Set-up slider
            $('#bet-input').slider({
                'min': parseInt(message.min_bet),
                'max': parseInt(message.max_bet),
                'value': parseInt(message.min_bet),
                'formatter': this.sliderHandler
            }).slider('setValue', parseInt(message.min_bet));

            // Fold control
            if (message.opening) {
                $('#fold-cmd').val('Pass')
                    .removeClass('btn-danger')
                    .addClass('btn-warning');
            }
            else {
                $('#fold-cmd').val('Fold')
                    .addClass('btn-danger')
                    .removeClass('btn-warning');
            }

            $('#fold-cmd-wrapper').show();
            $('#bet-input-wrapper').show();
            $('#bet-cmd-wrapper').show();
            $('#no-bet-cmd-wrapper').hide();
        }

        else {
            $('#fold-cmd-wrapper').hide();
            $('#bet-input-wrapper').hide();
            $('#bet-cmd-wrapper').hide();
            $('#no-bet-cmd-wrapper').show();
        }

        $('#bet-controls').show();
    },

    disableBetMode: function() {
        $('#bet-controls').hide();
    },

    setCardsChangeMode: function(changeMode) {
        this.cardsChangeMode = changeMode;

        if (changeMode) {
            $('#change-cards-controls').show();
        }
        else {
            $('#change-cards-controls').hide();
            $('#current-player .card.selected').removeClass('selected');
        }
    },

    setCard: function(cardKey, rank, suit) {
        $card = $('#current-player .card[data-key="' + cardKey + '"]');

        x = 0;
        y = 0;

        if ($card.hasClass('small')) {
            url = "static/images/cards-small.png";
            width = 45;
            height = 75;
        }
        else {
            url = "static/images/cards.png";
            width = 75;
            height = 125;
        }

        switch (suit) {
            case 0:
                // Spades
                x -= width;
                y -= height;
                break;
            case 1:
                // Clubs
                y -= height;
                break;
            case 2:
                // Diamonds
                x -= width;
                break;
            case 3:
                // Hearts
                break;
            default:
                throw "Invalid suit";
        }

        if (rank == 14) {
            rank = 1;
        }
        else if (rank < 1 || rank > 13) {
            throw "Invalid rank";
        }

        x -= (rank - 1) * 2 * width;

        $card.css('background-position', x + "px " + y + "px");
        $card.css('background-image', 'url(' + url + ')');
   },

    resetCards: function() {
        $('#current-player .card').each(function() {
            $card = $(this);
            $card.css('background-image', 'url(static/images/card-back.png)');
            $card.css('background-position', '0px 0px');
        });
        $('#current-player .cards .category').empty();
    }
}

$(document).ready(function() {
    Poker5.init()
    // Tests
//    Poker5.onConnect({
//        "msg_id": "connect",
//        "server": "server-123",
//        "player": {
//            "id": "12345-67890-abcde-fghij",
//            "name": "John Doe",
//            "money": 1000
//        }
//    });
//
//    Poker5.onGameUpdate({
//        "msg_id": "game-update",
//        "game": "game-123",
//        "event": "new-game",
//        "players": [
//            {
//                "id": "23456-67890-abcde-fghij",
//                "name": "Jim Morrison",
//                "money": 1000,
//                "alive": true,
//                "bet": 0
//            },
//            {
//                "id": "12345-67890-abcde-fghij",
//                "name": "John Doe",
//                "money": 1000,
//                "alive": true,
//                "bet": 0
//            }
//        ],
//        "pot": 0
//    });
//
//    Poker5.onSetCards({
//        "msg_id": "set-cards",
//        "cards": [[13, 3], [13, 2], [13, 1], [13, 0], [10, 3]],
//        "score": {
//            "category": 7,
//            "cards": [[13, 3], [13, 2], [13, 1], [13, 0], [10, 3]]
//        }
//    });
//
//    Poker5.onGameUpdate({
//        "msg_id": "game-update",
//        "player": 0,
//        "timeout": 60,
//        "game": "game-123",
//        "event": "player-action",
//        "players": [
//            {
//                "id": "23456-67890-abcde-fghij",
//                "name": "Jim Morrison",
//                "money": 1600,
//                "alive": true,
//                "bet": 0,
//                "score": {
//                    "cards": [[14, 3], [14, 2], [14, 1], [14, 0], [9, 2]],
//                    "category": 7
//                }
//            },
//            {
//                "id": "12345-67890-abcde-fghij",
//                "name": "John Doe",
//                "money": 400,
//                "alive": true,
//                "bet": 0,
//                "score": {
//                    "cards": [[13, 3], [13, 2], [13, 1], [13, 0], [10, 3]],
//                    "category": 7
//                }
//            }
//        ],
//        "pot": 0
//    });
})

