const ws_scheme = window.location.protocol == "https:" ? "wss" : "ws"

const gameSocket = new WebSocket(
    ws_scheme +
    '://'
    + window.location.host
    + '/ws/play/'
    + game_id
    + '/'
)

let got_my_cards = false
let round_started = 0
let my_number_of_cards
let cards_to_put_down = []
let selected_cards_id = []
let players_cards_n = []
let n_stacked_cards = 0
let player_names = []
let last_amount = 0

gameSocket.onmessage = function(e) {
    const data = JSON.parse(e.data)
    const type = data.type

    switch(type) {
        case "get_initial_hand":
            if(data.cards.length) {
                render_initial_cards(data.cards)
            }
            break
        case "player_info":
            n_stacked_cards = parseInt(data.stacked_cards)
            document.getElementById("stack_number").innerHTML = n_stacked_cards
        case "player_joined":
            fill_player_info_list(data)
            fill_player_column(data)
            break
        case "doubt":
            update_stacked_cards_count(-n_stacked_cards) // clears number of stacked cards
            handle_doubt(data)
            document.getElementById("curr_card").innerHTML = `<img class="card_icon" src="` + static_path_to_card_img + `icon-0.png" />`
            break
        case "round_start":
            // do something to declare new card for this round
            document.getElementById("curr_card").innerHTML = `<img class="card_icon" src="` + static_path_to_card_img + `icon-` + data.claimed + `.png" />`
            current_card = data.claimed
        case "cards_placed":
            last_amount = data.number
            update_stacked_cards_count(parseInt(data.number))
            update_card_count(turn, '-', parseInt(data.number))
            show_placing_animation(data.number) // show cards going to the stack
            show_card_placed_text(turn, data.number)
            update_turn() // pass onto next player
            break
        case "copies_removed":
            remove_copies((data.from)-1)
            break
    }
}

gameSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly');
}

document.querySelector('#place').onclick = function(e) {
    if(!(selected_cards_id.length) || my_player_num != turn)
        return
    if(n_stacked_cards) {
        gameSocket.send(JSON.stringify({
                'type': 'place_cards',
                'cards': cards_to_put_down,
            })
        )
    } else {
        if(document.getElementsByClassName("reminder").length) {
            $(".reminder").effect("shake")
            return
        }
        gameSocket.send(JSON.stringify({
                'type': 'start_round',
                'cards': cards_to_put_down,
                'claimed': $("input[name=card-choice]:checked").val(),
            })
        )
        $("input[name=card-choice]:checked").prop("checked", false)
        $("input[name=card-choice]").attr("disabled", true)
    }

    remove_cards_from_my_hand()
    cards_to_put_down = []
    selected_cards_id = []
    document.getElementById("n_selected_cards").innerHTML = '0'
}

document.querySelector('#doubt').onclick = function(e) {
    if(!n_stacked_cards)
        return
    gameSocket.send(JSON.stringify({
            'type': 'doubt'
        })
    )
}

update_turn = function() {
    last_player_col = document.getElementsByClassName("active_turn")[0]
    if(typeof(last_player_col) != "undefined") {
        last_player_col.classList.remove("active_turn")
    }

    last_turn = turn
    turn = (turn % n_players) + 1

    if(turn == my_player_num)
        document.getElementById("place").disabled = false
    else {
        document.getElementById("place").disabled = true
        document.getElementById("player_hand_" + (turn-1)).classList.add("active_turn")
    }
    
    if(turn != my_player_num)
        document.getElementById("turn_elem").innerHTML = player_names[turn-1]
    else
        document.getElementById("turn_elem").innerHTML = my_name
}

show_card_placed_text = function(player, number) { // shows dialog of player saying they put down an amount of cards
    if(player == my_player_num)
        return
        
    elem = document.getElementById("player_speaker_" + (player-1))
    show_player_text((player-1), number, 1)
}

// utility functions

play_doubt_animation = function(element_index, stack) { // shows "Dubito!" message and then reveals the stack of cards
    if(element_index != -1) {
        show_player_text(element_index, "Dubito!", 0)
    }
    
    show_stack(stack)
}

handle_doubt = function(data) {
    let element_index = data.who_doubted-1

    doubter = data.who_doubted
    doubted = last_turn
    modal_outcome = document.getElementById("doubt_outcome")
    last_card = current_card

    if(data.outcome) { // doubter wins
        if(doubted == my_player_num) { // I was doubted and I lost; add cards to my hand
            add_cards_to_player_hand(data.whole_stack)
            turn = doubter
            last_player_col = document.getElementsByClassName("active_turn")[0]
            if(typeof(last_player_col) != "undefined") {
                last_player_col.classList.remove("active_turn")
            }
            document.getElementById("player_hand_" + (turn-1)).classList.add("active_turn")
            modal_outcome.innerHTML = `<h5 class="ml3">Hai perso, prendi tutte le carte</h5>`
            animate_you_lose_doubt()
        } else { // 
            update_card_count(doubted, '+', data.whole_stack.length)
            turn = doubter
            if(my_player_num == doubter) { // I doubted and I won
                modal_outcome.innerHTML = `<h1 class="ml15">
                <span class="word">Hai dubitato correttamente!</span>
                <span class="word">Ora tocca a te</span>
              </h1>`
              animate_you_win_doubt()
              last_player_col = document.getElementsByClassName("active_turn")[0]
              if(typeof(last_player_col) != "undefined") {
                  last_player_col.classList.remove("active_turn")
              }
            } else {
                modal_outcome.innerHTML = `<h1 class="ml10">
                <span class="text-wrapper">
                  <span class="letters">` + player_names[doubter-1] + ` ha dubitato correttamente di ` + player_names[doubted-1] +`</span>
                </span>
              </h1>`
              animate_neutral_outcome_doubt()
              last_player_col = document.getElementsByClassName("active_turn")[0]
              if(typeof(last_player_col) != "undefined") {
                  last_player_col.classList.remove("active_turn")
              }
              document.getElementById("player_hand_" + (turn-1)).classList.add("active_turn")
            }
        }
    } else { // doubted wins
        if(doubter == my_player_num) { // I was the doubter and I lost; add cards to my hand
            add_cards_to_player_hand(data.whole_stack)
            turn = doubted
            last_player_col = document.getElementsByClassName("active_turn")[0]
            if(typeof(last_player_col) != "undefined") {
                last_player_col.classList.remove("active_turn")
            }
            document.getElementById("player_hand_" + (turn-1)).classList.add("active_turn")
            modal_outcome.innerHTML = `<h5 class="ml3">Hai sbagliato, prendi tutte le carte</h5>`
            animate_you_lose_doubt()
        } else { // someone else doubted
            update_card_count(doubter, '+', data.whole_stack.length)
            turn = doubted
            if(my_player_num == doubted) { // I was doubted and I won
                modal_outcome.innerHTML = `<h1 class="ml15">
                <span class="word">` + player_names[doubter-1] + ` ha sbagliato!</span>
                <span class="word">Ora tocca a te</span>
              </h1>`
              last_player_col = document.getElementsByClassName("active_turn")[0]
              if(typeof(last_player_col) != "undefined") {
                  last_player_col.classList.remove("active_turn")
              }
              animate_you_win_doubt()
            } else {
                modal_outcome.innerHTML = `<h1 class="ml10">
                <span class="text-wrapper">
                  <span class="letters">` + player_names[doubter-1] + ` ha dubitato di ` + player_names[doubted-1] +` e ha sbagliato</span>
                </span>
              </h1>`
              animate_neutral_outcome_doubt()
              last_player_col = document.getElementsByClassName("active_turn")[0]
              if(typeof(last_player_col) != "undefined") {
                  last_player_col.classList.remove("active_turn")
              }
              document.getElementById("player_hand_" + (turn-1)).classList.add("active_turn")
            }
        }
    }

    if(data.who_doubted != my_player_num) {
        play_doubt_animation(element_index, data.whole_stack)
    } else {
        play_doubt_animation(-1, data.whole_stack)
    }

    if(turn == my_player_num) {
        document.getElementById("place").disabled = false
        document.getElementById("turn_elem").innerHTML = my_name
    } else {
        document.getElementById("place").disabled = true
        document.getElementById("turn_elem").innerHTML = player_names[turn-1]
    }

}

// rendering functions

remove_copies = function(player) {
    jQuery(function($) {
        $('#cards_in_hand_' + (player)).countTo({
            from: players_cards_n[player],
            to: players_cards_n[player]-8,
            speed: 300,
            refreshInterval: 50,
            onComplete: function(value) {
                console.debug(this);
            }
        });
    });
    players_cards_n[player] -= 8
}

show_player_text = function(player, text, is_card) {
    if(!is_card) {
        $('#player_hand_' + player).attr("data-content", text)
    } else {
        final_text = text + "&nbsp;"
        card_icon_img = '<img src="' + static_path_to_card_img + 'icon-' + current_card + '.png" class="card_icon" />'
        final_text += card_icon_img + "!"
        $('#player_hand_' + player).attr("data-content", final_text)
    }
    
    $('#player_hand_' + player).popover("show")
}

update_stacked_cards_count = function(by) {
    old = n_stacked_cards
    n_stacked_cards += by
    console.log(n_stacked_cards)
    
    jQuery(function($) {
        $('#stack_number').countTo({
            from: old,
            to: n_stacked_cards,
            speed: 300,
            refreshInterval: 50,
            onComplete: function(value) {
                console.debug(this);
            }
        })
    })
    if(!n_stacked_cards) {
        document.getElementById("stack_number").innerHTML = '0'
    }
}

show_stack = async function(stack) { // shows modal containing the cards of the stack
    stacked_back = document.getElementById("stacked_back")
    stacked_front = document.getElementById("stacked_front")
    for(let i = 0; i < last_amount; i++) {
        this_card = stack[stack.length-i-1]
        stacked_back.src = static_path_to_card_img + this_card + ".png"
        j = 0 // used to prevent doubling of post-flipping function when card is flipped back
        $("#stacked_card").on("flip:done", function(){
            if((j%2)) return
            j++
            $("#stacked_card").animate({
                'right' : "0" //moves right
            }, 200, function() {
                $("#hidden_uncovered_card_div").fadeIn(0)
                document.getElementById("hidden_uncovered_card").src = static_path_to_card_img + this_card + ".png" 
                $("#stacked_card").fadeOut(0,0);
                $("#stacked_card").css("right","25%")
                $("#stacked_card").flip(false)
            })
        })
        $("#stacked_card").fadeIn(0);
        $("#stacked_card").flip(true)
        await new Promise(r => setTimeout(r, 1000));
    }
    $("#stack_modal").modal("show")
    const modal_body = document.getElementById("stack_modal_body")

    for(card of stack) {
        modal_body.innerHTML += `<div class="card-grid flip_card"> 
            <div class="front"> 
                <img class='card_in_hand' src='` + static_path_to_card_img + `red_back.png' />
            </div> 
            <div class="back">
                <img class='card_in_hand' src='` + static_path_to_card_img + card + `.png' />
            </div> 
        </div> `
        $(".card-grid").flip()
        $(".flip_card").flip()
    }
    setTimeout(function() {$(".flip_card").flip("toggle")}, 500)
    if(turn == my_player_num) {
        setTimeout(function() {
            hide_stack()
            animate_begin_round()
        }, 1500+(250*stack.length))
    } else {
        setTimeout(hide_stack, 1500+(250*stack.length))
    }
}

hide_stack = function() {
    $("#stack_modal").modal("hide")
    $("#hidden_uncovered_card").attr("src", "")
    clear_stack() // erase html content of the modal that shows stacked cards when doubt is called
}

clear_stack = function() {
    document.getElementById("stack_modal_body").innerHTML = ""
}

render_initial_cards = function(cards) {
    if(got_my_cards)
        return
    got_my_cards = true
    let i = 0
    my_cards = document.getElementById("my_cards")
    for(card of cards) {
        my_cards.innerHTML += "<img id='my_card_" + i + "' class='" + card.card_number + card.card_seed + " card_in_hand selectable_card' src='" + static_path_to_card_img + card.card_number + card.card_seed + ".png' />"
        i++
    }
    my_number_of_cards = i
    jQuery(function($) {
        $('#my_card_count').countTo({
            from: 0,
            to: my_number_of_cards,
            speed: 300,
            refreshInterval: 50,
            onComplete: function(value) {
                console.debug(this);
            }
        });
    });
    bind_event_listeners()
}

remove_cards_from_my_hand = function() { // removes cards that were put down from div containing your cards
    old_amount = my_number_of_cards
    for(card of selected_cards_id) {
        $("#" + card).fadeOut(100) // use some animation here
        document.getElementById(card).outerHTML = ""
        move_card_to_stack(card)
        my_number_of_cards--
    }
    jQuery(function($) {
        $('#my_card_count').countTo({
            from: old_amount,
            to: my_number_of_cards,
            speed: 300,
            refreshInterval: 50,
            onComplete: function(value) {
                console.debug(this);
            }
        });
    });
}

fill_player_column = function(data) { // fills column corresponding to player who just entered with their name and number of cards
    element_index = data.player_number - 1 // -1 because player numbers are 1-indexed, whereas player columns are 0-indexed
    col = document.getElementById("player_col_" + element_index)
    
    document.getElementById("cards_in_hand_" + element_index).innerHTML =  data.number_of_cards
    document.getElementById("player_name_" + element_index).innerHTML = data.player_name
}

fill_player_info_list = function(data) {
    element_index = data.player_number - 1 // -1 because player numbers are 1-indexed, whereas player columns are 0-indexed
    players_cards_n[element_index] = data.number_of_cards
    player_names[element_index] = data.player_name
}

update_card_count = function(player, operation, number) {
    if(player == my_player_num)
        return
    idx = player
    console.log((players_cards_n[idx-1]) + operation + number)
    res = eval(parseInt(players_cards_n[idx-1]) + operation + number)
    jQuery(function($) {
        $('#cards_in_hand_' + (idx-1)).countTo({
            from: parseInt(players_cards_n[idx-1]),
            to: res,
            speed: 300,
            refreshInterval: 50,
            onComplete: function(value) {
                console.debug(this);
            }
        });
    });
    players_cards_n[idx-1] = res
    console.log("cards_in_hand_"+(idx-1))
}

add_cards_to_player_hand = function(cards) { // displays new cards that were added to player's hand because they lost a round
    my_cards = document.getElementById("my_cards")
    old_card_count = my_number_of_cards
    for(card of cards) {
        my_number_of_cards++
        my_cards.innerHTML += "<img id='my_card_" + my_number_of_cards + "' class='" + card + " card_in_hand selectable_card' src='" + static_path_to_card_img + card + ".png' />"
    }
    bind_event_listeners()
    jQuery(function($) {
        $('#my_card_count').countTo({
            from: old_card_count,
            to: my_number_of_cards,
            speed: 300,
            refreshInterval: 50,
            onComplete: function(value) {
                console.debug(this);
            }
        });
    });

    // check if player has 8 of any card
    for(let i = 1; i <= 13; i++) {
         // gotta do it the ugly way for aces
         if((i == 1 && document.getElementsByClassName("1C").length + document.getElementsByClassName("1H").length + document.getElementsByClassName("1S").length + document.getElementsByClassName("1D").length == 8)) {
             $(".1C").fadeOut(100)
             $(".1D").fadeOut(100)
             $(".1H").fadeOut(100)
             $(".1S").fadeOut(100, function() {
                $('.1C').remove()
                $('.1D').remove()
                $('.1H').remove()
                $('.1S').remove()
            })
            jQuery(function($) {
                $('#my_card_count').countTo({
                    from: my_number_of_cards,
                    to: my_number_of_cards-8,
                    speed: 300,
                    refreshInterval: 50,
                    onComplete: function(value) {
                        console.debug(this);
                    }
                })
            })
            my_number_of_cards -= 8            
         }
         // a little better for all the other cards
         if(i != 1 && document.querySelectorAll('img[class^="' + i + '"]').length == 8) {
            $('img[class^="' + i +'"]').fadeOut(100, function() {
                $('img[class^="' + i +'"]').remove()
            })
            jQuery(function($) {
                $('#my_card_count').countTo({
                    from: my_number_of_cards,
                    to: my_number_of_cards-8,
                    speed: 300,
                    refreshInterval: 50,
                    onComplete: function(value) {
                        console.debug(this);
                    }
                })
            })
            my_number_of_cards -= 8            
        }
    }
}

begin_game = function() {
    if(my_player_num == turn && n_stacked_cards == 0) {
        animate_begin_round()
    }
}

show_card_selection_dialog = function() {
    $("#card_selection_modal").modal("show")
}

/* generate deck
seeds = ['H','S','D','C']
cards = []
for(let i = 1; i <= 13; i++) {
    for(let j = 0; j < 3; j++) {
        str = i + seeds[j]
        cards.push(str)
    }

            deck = ["1H","1H","1S","1S","1D","1D","1C","1C","2H","2H","2S","2S","2D","2D","2C","2C","3H",
            "3H","3S","3S","3D","3D","3C","3C","4H","4H","4S","4S","4D","4D","4C","4C","5H","5H","5S","5S","5D",
            "5D","5C","5C","6H","6H","6S","6S","6D","6D","6C","6C","7H","7H","7S","7S","7D","7D","7C","7C","8H","8H","8S","8S","8D",
            "8D","8C","8C","9H","9H","9S","9S","9D","9D","9C","9C","10H","10H","10S","10S","10D","10D","10C","10C","11H","11H","11S",
            "11S","11D","11D","11C","11C","12H","12H","12S","12S","12D","12D","12C","12C","13H","13H","13S","13S","13D","13D","13C",
            "13C","JOK","JOK","JOK","JOK"]
}*/