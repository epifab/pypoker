Poker5 = {
    socket: null,

    betMode: false,

    cardsChangeMode: true,

    playerId: null,

    players: [],

    init: function() {
        if (window.location.protocol == "https:") {
            var ws_scheme = "wss://";
        }
        else {
            var ws_scheme = "ws://"
        }

        this.socket = new WebSocket(ws_scheme + location.host + "/poker5");

        this.socket.onopen = function() {
            $("#game-log").append($("<p></p>").text('Connected :)'));
        };

        this.socket.onclose = function() {
            $("#game-log").append($("<p></p>").text('Connection lost :('));
        };

        this.socket.onmessage = function(message) {
            var data = JSON.parse(message.data);

            console.log(data);

            switch (data.msg_id) {
                case 'connect':
                    Poker5.playerId = data.player.id;
                    break;
                case 'disconnect':
                    break;
                case 'set-cards':
                    for (cardKey in data.cards) {
                        Poker5.setCard(Poker5.playerId, cardKey + 1, data.cards[cardKey][0], data.cards[cardKey[1]]);
                    }
                    break;
                case 'game-status':
                    break;
                case 'game-update':
                    if (data['phase'] == 'cards-assignment') {
                        Poker5.players = [];

                        $('#players').empty();

                        for (key in data.players) {
                            player = data.players[key];

                            Poker5.players.push(player);

                            $('#players').append(
                                '<div class="player player-' + player.id + '">'
                                + '<div class="cards row">'
                                + '<div class="card small card-1 pull-left"></div>'
                                + '<div class="card small card-2 pull-left"></div>'
                                + '<div class="card small card-3 pull-left"></div>'
                                + '<div class="card small card-4 pull-left"></div>'
                                + '<div class="card small card-5 pull-left"></div>'
                                + '</div>'
                                + '<div class="player-info">'
                                + '<span class="player-name">' + player.name + '</span>'
                                + ' - '
                                + '<span class="player-money">$' + player.money + '.00</span>'
                                + '</div>'
                                + '</div>');
                        }
                    }
                    break;
            }
        };


        $('#player-control .card').click(function() {
            if (Poker5.cardsChangeMode) {
                $(this).toggleClass('selected');
            }
        })

        $('#change-cards-cmd').click(function() {
            if (Poker5.cardsChangeMode) {
                cards = $('#player-control .card.selected')
                console.log(cards)
                Poker5.setCardsChangeMode(false)
            }
        })

        this.setBetMode(false)
        this.setCardsChangeMode(false)
    },

    setBetMode: function(betMode) {
        this.betMode = betMode;

        if (betMode) {
            $('#bet-group').show()
        }
        else {
            $('#bet-group').hide()
        }
    },

    setCardsChangeMode: function(changeMode) {
        this.cardsChangeMode = changeMode;

        if (changeMode) {
            $('#change-cards-cmd').show()
        }
        else {
            $('#change-cards-cmd').hide()
        }
    },

    setCard: function(playerId, cardId, rank, suit) {
        $('.player-' + playerId + ' .card-' + cardId).each(function() {
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

            if (rank < 1 || rank > 13) {
                throw "Invalid rank";
            }

            x -= (rank - 1) * 2 * width;

            $element.css('background-position', x + "px " + y + "px");
            $element.css('background-image', 'url(' + url + ')');

            $element.data('rank', rank)
            $element.data('suit', suit)
        })
    }
}

$(document).ready(function() {
    Poker5.init()

    /*
    Poker5.setCard(1, 1, 13, 2);
    Poker5.setCard(1, 2, 12, 2);
    Poker5.setCard(1, 3, 11, 2);
    Poker5.setCard(1, 4, 10, 2);
    Poker5.setCard(1, 5, 9, 2);

    Poker5.setCard(2, 1, 1, 3);
    Poker5.setCard(2, 2, 1, 2);
    Poker5.setCard(2, 3, 1, 1);
    Poker5.setCard(2, 4, 1, 0);
    Poker5.setCard(2, 5, 9, 2);
    $('.player-2').css('opacity', 0.5)

    Poker5.setCard(3, 1, 7, 2);
    Poker5.setCard(3, 2, 8, 2);
    Poker5.setCard(3, 3, 9, 3);
    Poker5.setCard(3, 4, 10, 1);
    Poker5.setCard(3, 5, 11, 1);
    $('.player-4').css('opacity', 0.5)

    // Simulate Player 4 fold
    $('.player-4 .card').css('opacity', 0.5);
    */
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