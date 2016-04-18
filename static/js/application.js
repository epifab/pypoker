Poker5 = {
    socket: null,

    betMode: false,

    cardsChangeMode: true,

    log: function(text) {
        $('#game-log').append($('<p></p>').text(text))
    },

    init: function() {
        if (window.location.protocol == "https:") {
            var ws_scheme = "wss://";
        }
        else {
            var ws_scheme = "ws://"
        }

        this.socket = new WebSocket(ws_scheme + location.host + "/poker5");

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
                case 'join-lobby':
                    Poker5.onJoinLobby(data);
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

        $('#player-control .card').click(function() {
            if (Poker5.cardsChangeMode) {
                $(this).toggleClass('selected');
            }
        });

        $('#change-cards-cmd').click(function() {
            discards = [];
            $('#player-control .card.selected').each(function() {
                discards.push($(this).data('key'))
            });
            Poker5.socket.send(JSON.stringify({
                'msg_id': 'change-cards',
                'cards': discards
            }));
            Poker5.setCardsChangeMode(false);
        });

        $('#fold-cmd').click(function() {
            Poker5.socket.send(JSON.stringify({
                'msg_id': 'bet',
                'bet': -1
            }));
            Poker5.setBetMode(false);
        });

        $('#bet-cmd').click(function() {
            Poker5.socket.send(JSON.stringify({
                'msg_id': 'bet',
                'bet': $('#bet-input').val()
            }));
            Poker5.setBetMode(false);
        });

        this.setCardsChangeMode(false);
        this.setBetMode(false);
    },

    onGameUpdate: function(message) {
        if (message.phase == 'new-game') {
            this.initGame(message);
        }
        this.updateGame(message);

        switch (message.phase) {
            case 'new-game':
                break;
            case 'cards-assignment':
                this.log('New hand');
                break;
            case 'opening-bet':
            case 'final-bet':
                player = message.players[message.player];
                switch (message.bet_type) {
                    case 'FOLD':
                        this.log(player.name + ": FOLD");
                        break;
                    case 'PASS':
                        this.log(player.name + ": PASS");
                        break;
                    case 'CHECK':
                        this.log(player.name + ": CHECK");
                        break;
                    case 'CALL':
                    case 'RAISE':
                        this.log(player.name + ": BET $" + parseInt(message.bet) + ".00 (" + message.bet_type + ")");
                        break;
                }
                break;
            case 'cards-change':
                Poker5.log("Player " + message.players[message.player].name + " changed " + message.num_cards + " cards.");
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
        Poker5.setBetMode(false);
        Poker5.setCardsChangeMode(false);
    },

    onJoinLobby: function(message) {
        this.log(message.player.name + " has joined the lobby (" + message.players.length + " players waiting to play)");
    },

    onSetCards: function(message) {
        for (cardKey in message.cards) {
            Poker5.setCard(
                $('#player-control').data('id'),
                cardKey,
                message.cards[cardKey][0],
                message.cards[cardKey][1]);
        }
    },

    onBet: function(message) {
        Poker5.setBetMode(true);
    },

    onChangeCards: function(message) {
        this.setCardsChangeMode(true);
    },

    initGame: function(message) {
        $('#players').empty();

        for (key in message.players) {
            player = message.players[key];

            $('#players').append(
                '<div class="player" data-id="' + player.id + '">'
                + '<div class="cards row">'
                + '<div class="card small pull-left" data-key="0"></div>'
                + '<div class="card small pull-left" data-key="1"></div>'
                + '<div class="card small pull-left" data-key="2"></div>'
                + '<div class="card small pull-left" data-key="3"></div>'
                + '<div class="card small pull-left" data-key="4"></div>'
                + '</div>'
                + '<div class="player-info">'
                + '<span class="player-name">' + player.name + '</span>'
                + ' - '
                + '<span class="player-money">$' + parseInt(player.money) + '.00</span>'
                + '</div>'
                + '</div>');
        }
    },

    updateGame: function(message) {
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
            $('.player[data-id="' + player.id + '"] .player-money').text("$" + parseInt(player.money) + ".00");

            if (player.alive) {
                $('.player[data-id="' + player.id + '"]').css('opacity', 100);
            }
            else {
                $('.player[data-id="' + player.id + '"]').css('opacity', 50);
            }

            if (key == message.player) {
                $('.player[data-id="' + player.id + '"]').addClass('selected');
            }
            else {
                $('.player[data-id="' + player.id + '"]').removeClass('selected');
            }
        }
    },

    setBetMode: function(betMode) {
        this.betMode = betMode;

        if (betMode) {
            $('#bet-group').show();
        }
        else {
            $('#bet-group').hide();
        }
    },

    setCardsChangeMode: function(changeMode) {
        this.cardsChangeMode = changeMode;

        if (changeMode) {
            $('#change-cards-cmd').show();
        }
        else {
            $('#change-cards-cmd').hide();
            $('#player-control .card.selected').removeClass('selected');
        }
    },

    setCard: function(playerId, cardKey, rank, suit) {
        $('.player[data-id="' + playerId + '"] .card[data-key="' + cardKey + '"]').each(function() {
            $element = $(this);

            x = 0;
            y = 0;

            if ($element.hasClass('small')) {
                url = "static/images/cards-small.jpg";
                width = 45;
                height = 75;
            }
            else {
                url = "static/images/cards.jpg";
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

            $element.data('rank', rank);
            $element.data('suit', suit);
        })
    }
}

$(document).ready(function() {
    Poker5.init()
})


/*
var inbox = new ReconnectingWebSocket(ws_scheme + location.host + "/receive");
var outbox = new ReconnectingWebSocket(ws_scheme + location.host + "/submit");

inbox.onmessage = function(message) {
  var data = JSON.parse(message.data);
  $("#chat-text").append("<div class='panel panel-default'><div class='panel-heading'>" + $('<span/>').text(data.handle).html() + "</div><div class='panel-body'>" + $('<span/>').text(data.text).html() + "</div></div>");
  $("#chat-text").stop().animate({
    scrollTop: $('#chat-text')[0].scrollHeight
  }, 800);
};

inbox.onclose = function(){
    console.log('inbox closed');
    this.inbox = new WebSocket(inbox.url);

};

outbox.onclose = function(){
    console.log('outbox closed');
    this.outbox = new WebSocket(outbox.url);
};

$("#input-form").on("submit", function(event) {
  event.preventDefault();
  var handle = $("#input-handle")[0].value;
  var text   = $("#input-text")[0].value;
  outbox.send(JSON.stringify({ handle: handle, text: text }));
  $("#input-text")[0].value = "";
});
*/