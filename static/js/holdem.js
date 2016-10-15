Game = {
    gameId: null,
    
    players: null,
    
    getPlayers: function() {
        return $('#players .player');
    },
    
    getPlayer: function(playerId) {
        return $('#players .player[data-id="' + playerId + '"]');
    },
    
    newGame: function(message) {
        this.gameId = message.game_id;
        this.players = message.players;

        for (playerId in message.players) {
            $player = this.getPlayer(playerId);
            $player.append($('<div class="cards"></div>'));
            $player.append($('<div class="bet"></div>'));
            if (playerId == message.dealer_id) {
                $player.addClass('dealer');
            }
            if (playerId == $('#current-player').attr('data-id')) {
                $player.addClass('current');
            }
        }
    },
    
    gameOver: function(message) {
        $('.player').removeClass('winner');
        $('.player').removeClass('dealer');
        $('#pots').empty();
        $('.player .cards').remove();
        $('.player .bet').remove();
    },
    
    updatePlayer: function(player) {
        $player = this.getPlayer(player.id);
        $('.player-money', $player).text('$' + parseInt(player.money));
        $('.player-name', $player).text(player.name);
    },

    updatePlayersBet: function(bets) {
        $('.bet', this.getPlayers()).empty();
        if (bets !== undefined) {
            for (playerId in bets) {
                $('.bet', this.getPlayer(playerId)).text('$' + parseInt(bets[playerId]));
            }
        }
    },
    
    updatePlayersCards: function(cards) {
        for (playerId in cards) {
            $cards = $('.cards', this.getPlayer(playerId));
            $cards.empty();
            for (cardKey in cards[playerId].cards) {
                rank = this.getRank(cards[playerId][cardKey]);
                suit = this.getSuit(cards[playerId][cardKey]);
                $cards.append($(
                    '<div class="card text" data-suit="' + suit + '">' +
                    '<div class="rank">' + rank + '</div>' +
                    '<div class="suit">&' + suit + ';</div>' +
                    '</div>'
                ));
            }
        }
    },
    
    updatePots: function(pots) {
        $('#pots').empty();
        for (potIndex in pots) {
            $('#pots').append($(
                '<div class="pot">' +
                '$' + parseInt(message.pots[potIndex].money) +
                '</div>'
            ));
        }
    },
    
    getRank: function(card) {
        switch (card[0]) {
            case 11:
                return 'J';
            case 12:
                return 'Q';
            case 13:
                return 'K';
            case 1:
            case 14:
                return 'A';
            default:
                return card[0];
        }
    },
    
    getSuit: function(card) {
        switch (card[1]) {
            case 3:
                return "hearts";
            case 2:
                return "diams";
            case 1:
                return "clubs";
            default:
                return "spades";
        }
    }
}


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
            Poker5.destroyRoom();
        };

        this.socket.onmessage = function(message) {
            var data = JSON.parse(message.data);

            console.log(data);

            switch (data.message_type) {
                case 'ping':
                    Poker5.socket.send(JSON.stringify({'message_type': 'pong'}));
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
                'message_type': 'change-cards',
                'cards': discards
            }));
            Poker5.setCardsChangeMode(false);
        });

        $('#fold-cmd, #no-bet-cmd').click(function() {
            Poker5.socket.send(JSON.stringify({
                'message_type': 'bet',
                'bet': -1
            }));
            Poker5.disableBetMode();
        });

        $('#bet-cmd').click(function() {
            Poker5.socket.send(JSON.stringify({
                'message_type': 'bet',
                'bet': $('#bet-input').val()
            }));
            Poker5.disableBetMode();
        });

        this.setCardsChangeMode(false);
        this.disableBetMode();
    },

    onGameUpdate: function(message) {
        if (message.event == 'game-over') {
            this.destroyGame();
        }

        this.resetControls();
        this.resetTimers();

        HoldemGame.updatePlayersBet(message.bets);

        switch (message.event) {
            case 'new-game':
                Game.newGame(message);
            case 'bet':
                Game.updatePlayer(message.player);
                break;
            case 'pots-update':
                Game.updatePots(message.pots);
                break;
            case 'player-action':
                this.onPlayerAction(message);
                break;
            case 'dead-player':
                // Will be handled by an upcoming room-update message
                break;
            case 'add-shared-cards':
                // Not supported yet
                // Game.addSharedCards(message.cards);
                break;
            case 'winner-designation':
                Game.updatePots(message.pots);
                Game.showPotWinners(message.pot);
                break;
            case 'showdown':
                Game.updatePlayersCards(message.players);
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
        Poker5.log(message.error);
    },

    onTimeout: function(message) {
        Poker5.log('Time is up!');
        Poker5.disableBetMode();
        Poker5.setCardsChangeMode(false);
    },

    createPlayer: function(player=undefined) {
        if (player === undefined) {
            return $('<div class="player"><div class="player-info"></div></div>');
        }
        isCurrentPlayer = player.id == $('#current-player').data('id');

        $playerName = $('<p class="player-name"></p>');
        $playerName.text(isCurrentPlayer ? 'You' : player.name);

        $playerMoney = $('<p class="player-money"></p>');
        $playerMoney.text('$' + parseInt(player.money));

        $playerInfo = $('<div class="player-info"></div>');
        $playerInfo.append($playerName);
        $playerInfo.append($playerMoney);

        $player = $('<div class="player' + (isCurrentPlayer ? ' current' : '') + '"></div>');
        $player.attr('data-id', player.id);
        $player.append($('<div class="cards"></div>'));
        $player.append($playerInfo);
        $player.append($('<div class="timer"></div>'));
        $player.append($('<div class="bet"></div>'));

        return $player;
    },

    destroyRoom: function() {
        this.destroyGame();
        this.roomId = null;
        $('#players').empty();
    },

    initRoom: function(message) {
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
                $seat.attr('data-player-id', playerId);
            }
            else {
                $seat.append(this.createPlayer());
                $seat.attr('data-player-id', null);
            }
            $('#players').append($seat);
        }
    },

    onRoomUpdate: function(message) {
        switch (message.event) {
            case 'init':
                this.initRoom(message);
                break;

            case 'player-added':
                playerId = message.player_id;
                player = message.players[playerId]
                playerName = playerId == $('#current-player').data('id') ? 'You' : player.name;
                // Go through every available seat, find the one where the new player should sat and seated him
                $('.seat').each(function() {
                    seat = $(this).attr('data-key');
                    if (message.player_ids[seat] == playerId) {
                        $(this).empty();
                        $(this).append(Poker5.createPlayer(player));
                        $(this).attr('data-player-id', playerId);
                        return;
                    }
                });
                this.log(playerName + " joined the room");
                break;

            case 'player-removed':
                playerId = message.player_id;
                playerName = $('.player[data-id=' + playerId + '] .player-name').text();
                // Go through every available seat, find the one where the leaving player sat and kick him out
                $('.seat').each(function() {
                    seatedPlayerId = $(this).attr('data-player-id');
                    if (seatedPlayerId == playerId) {
                        $(this).empty();
                        $(this).append(Poker5.createPlayer());
                        $(this).attr('data-player-id', null);
                        return;
                    }
                });
                this.log(playerName + " left the room");
                break;
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

    onPlayerAction: function(message) {
    console.log(message.player);
        isCurrentPlayer = message.player.id == $('#current-player').data('id');

        switch (message.action) {
            case 'bet':
                if (isCurrentPlayer) {
                    this.log('Your turn to bet');
                    this.onBet(message);
                }
                else {
                    this.log('Waiting for ' + message.player.name + ' to bet...');
                }
                break;
            case 'change-cards':
                if (isCurrentPlayer) {
                    this.log('Your turn to change cards');
                    this.onChangeCards(message);
                }
                else {
                    this.log('Waiting for ' + message.player.name + ' to change cards...');
                }
                break;
        }

        $timers = $('.player[data-id="' + message.player_id + '"] .timer');
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
    Poker5.init();
})

