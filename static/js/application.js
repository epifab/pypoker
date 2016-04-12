// Support TLS-specific URLs, when appropriate.
if (window.location.protocol == "https:") {
  var ws_scheme = "wss://";
} else {
  var ws_scheme = "ws://"
};


// var poker = new ReconnectingWebSocket(ws_scheme + location.host + "/connect");

Card = {
    show($element, rank, suit) {
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
                x -= width;
                y -= height;
                break;
            case 1:
                y -= height;
                break;
            case 2:
                x -= width;
            case 3:
                break;
        }

        x -= (rank - 1) * 2 * width;

        $element.css('background-position', x + "px " + y + "px");
        $element.css('background-image', 'url(' + url + ')');
    }
}

$(document).ready(function() {
    var card1 = $('.player-1 .card-1');
    var card2 = $('.player-1 .card-2');
    var card3 = $('.player-1 .card-3');
    var card4 = $('.player-1 .card-4');
    var card5 = $('.player-1 .card-5');

    Card.show(card1, 8, 0);
    Card.show(card2, 8, 3);
    Card.show(card3, 8, 1);

    var card1 = $('.player-2 .card-1');
    var card2 = $('.player-2 .card-2');
    var card3 = $('.player-2 .card-3');
    var card4 = $('.player-2 .card-4');
    var card5 = $('.player-2 .card-5');

    Card.show(card1, 13, 2);
    Card.show(card2, 13, 3);
    Card.show(card3, 12, 3);
    Card.show(card4, 7, 3);
    Card.show(card5, 9, 0);

    $('.player-2 .card').css('opacity', 0.6);

    var card1 = $('.player-3 .card-1');
    var card2 = $('.player-3 .card-2');
    var card3 = $('.player-3 .card-3');
    var card4 = $('.player-3 .card-4');
    var card5 = $('.player-3 .card-5');

    Card.show(card1, 1, 0);
    Card.show(card2, 11, 3);
    Card.show(card3, 12, 1);
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