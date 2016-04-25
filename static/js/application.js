Poker5 = {
    socket: null,

    betMode: false,

    cardsChangeMode: true,

    log: function(text) {
        $('#game-log').append($('<p></p>').text(text));
    },

    clearLogs: function() {
        $('#game-log').empty();
    },

    init: function() {
        if (window.location.protocol == "https:") {
            var ws_scheme = "wss://";
        }
        else {
            var ws_scheme = "ws://"
        }

        this.socket = new WebSocket("wss://pypoker.herokuapp.com/poker5");
//        this.socket = new WebSocket(ws_scheme + location.host + "/poker5");

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
                case 'connect':
                    Poker5.onConnect(data);
                    break;
                case 'disconnect':
                    Poker5.onDisconnect(data);
                    break;
                case 'lobby-update':
                    Poker5.onLobbyUpdate(data);
                    break;
                case 'set-cards':
                    Poker5.onSetCards(data);
                    break;
                case 'change-cards':
                    Poker5.onChangeCards(data);
                    break;
                case 'bet':
                    Poker5.onBet(data);
                    break;
                case 'game-update':
                    Poker5.onGameUpdate(data);
                    break;
                case 'error':
                    Poker5.log('Error received: ' + data.error)
                    break;
                case 'timeout':
                    Poker5.log('Timed out')
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
        this.updateGame(message);

        switch (message.event) {
            case 'new-game':
                break;
            case 'game-over':
                break;
            case 'cards-assignment':
                this.clearLogs();
                this.log('New hand');
                break;
            case 'bet':
                this.disablePlayerAction();
                player = message.players[message.player];
                switch (message.bet_type) {
                    case 'fold':
                    case 'pass':
                    case 'check':
                        this.log(player.name + " " + message.bet_type);
                        break;
                    case 'open':
                    case 'call':
                    case 'raise':
                        this.log(player.name + " bet $" + parseInt(message.bet) + " (" + message.bet_type + ")");
                        break;
                }
                break;
            case 'cards-change':
                this.disablePlayerAction();
                Poker5.log("Player " + message.players[message.player].name + " changed " + message.num_cards + " cards.");
                break;
            case 'player-action':
                Poker5.enablePlayerAction(message.players[message.player].id, message.timeout);
                break;
            case 'winner-designation':
                Poker5.log("Player " + message.players[message.player].name + " won!");
                break;
        }
    },

    onConnect: function(message) {
        this.log("Connection established with poker5 server: " + message.server);
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

    onLobbyUpdate: function(message) {
        switch (message.event) {
            case 'player-added':
                this.log(message.player.name + " joined the lobby");
                break;
            case 'player-removed':
                this.log(message.player.name + " left the lobby");
                break;
        }
    },

    onSetCards: function(message) {
        for (cardKey in message.cards) {
            Poker5.setCard(
                $('#current-player').data('id'),
                cardKey,
                message.cards[cardKey][0],
                message.cards[cardKey][1]);
        }
    },

    onBet: function(message) {
        Poker5.enableBetMode(message);
    },

    onChangeCards: function(message) {
        this.setCardsChangeMode(true);
    },

    initGame: function(message) {
        $('#players').empty();

        for (key in message.players) {
            player = message.players[key];

            playerClass = 'player';
            if (player.id == $('#current-player').data('id')) {
                playerClass += ' current';
            }

            $('#players').append(
                '<div class="' + playerClass + '" data-id="' + player.id + '">'
                + '<div class="cards row">'
                + '<div class="card small pull-left" data-key="0"></div>'
                + '<div class="card small pull-left" data-key="1"></div>'
                + '<div class="card small pull-left" data-key="2"></div>'
                + '<div class="card small pull-left" data-key="3"></div>'
                + '<div class="card small pull-left" data-key="4"></div>'
                + '</div>'
                + '<div class="player-info">'
                + '<p class="player-name">' + player.name + '</p>'
                + '<p class="player-money">$' + parseInt(player.money) + '</p>'
                + '</div>'
                + '<div class="timer"></div>'
                + '<div class="bet"></div>'
                + '</div>');
        }
    },

    updateGame: function(message) {
        if (message.event == "new-game") {
            this.initGame(message);
        }

        $('#pot').text("$" + parseInt(message.pot));

        for (key in message.players) {
            player = message.players[key]
            if (player.score) {
                for (cardKey in player.score.cards) {
                    Poker5.setCard(
                        player.id,
                        cardKey,
                        player.score.cards[cardKey][0],
                        player.score.cards[cardKey][1]);
                }
            }
            else if (player.id != $('#current-player').data('id')) {
                $('.player[data-id="' + player.id + '"] .card').each(function() {
                    $(this).css('background-position', '');
                    $(this).css('background-image', '');
                });
            }
            $('.player[data-id="' + player.id + '"] .player-money').text("$" + parseInt(player.money));
            $('.player[data-id="' + player.id + '"] .bet').text("$" + parseInt(player.bet));

            if (player.alive) {
                $('.player[data-id="' + player.id + '"]').css('opacity', 100);
            }
            else {
                $('.player[data-id="' + player.id + '"]').css('opacity', 50);
            }
        }
    },

    enablePlayerAction: function(playerId, timeout) {
        $timers = $('.player[data-id="' + playerId + '"] .timer');
        $timers.data('timer', timeout);
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

    disablePlayerAction: function() {
        $activeTimers = $('.timer.active');
        $activeTimers.TimeCircles().destroy();
        $activeTimers.removeClass('active');
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

        if (message.max_bet == -1) {
            $('#fold-cmd-wrapper').hide();
            $('#bet-input-wrapper').hide();
            $('#bet-cmd-wrapper').hide();
            $('#no-bet-cmd-wrapper').show();
        }

        else {
            // Set-up slider
            $('#bet-input').slider({
                'min': parseInt(message.min_bet),
                'max': parseInt(message.max_bet),
                'value': parseInt(message.min_bet),
                'formatter': this.sliderHandler
            });
            this.sliderHandler(message.min_bet);

            $('#fold-cmd-wrapper').show();
            $('#bet-input-wrapper').show();
            $('#bet-cmd-wrapper').show();
            $('#no-bet-cmd-wrapper').hide();
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

    setCard: function(playerId, cardKey, rank, suit) {
        $('.player[data-id="' + playerId + '"] .card[data-key="' + cardKey + '"]').each(function() {
            $element = $(this);

            x = 0;
            y = 0;

            if ($element.hasClass('small')) {
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

            $element.css('background-position', x + "px " + y + "px");
            $element.css('background-image', 'url(' + url + ')');
        })
    }
}

function getTestGameMessage() {
    return {
        "msg_id": "game-update",
        "event": "new-game",
        "players": [
            {"id": "leonard", "name": "Leonard", "money": 10000.0, "alive": true , "bet": 0.0},
            {"id": "michael", "name": "Michael", "money": 10000.0, "alive": true, "bet": 0.0},
            {"id": $('#current-player').data('id'), "name": "You", "money": 10000.0, "alive": true, "bet": 0.0},
            {"id": "charles", "name": "Charles", "money": 10000.0, "alive": true, "bet": 0.0}
        ],
        "pot": 0.0
    }
}

$(document).ready(function() {
    Poker5.init()
    // Tests
//    message = getTestGameMessage();
//    Poker5.onGameUpdate(message);
//    message.players[0].money = 9900;
//    message.players[1].money = 9900;
//    message.players[2].money = 9900;
//    message.players[3].money = 9900;
//    message.pot = 400;
//    message.event = "cards-assignment";
//    Poker5.onGameUpdate(message)
})

