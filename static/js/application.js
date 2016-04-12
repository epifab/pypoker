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

        switch (suit) {
            case 0:
                x = -75;
                y = -125;
                break;
            case 1:
                y = -125;
                break;
            case 2:
                x = -75;
            case 3:
                break;
        }

        x -= (rank - 1) * 150;

        $element.css('background-position', x + "px " + y + "px");
        $element.css('background-image', 'url(../static/images/cards.jpg');
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