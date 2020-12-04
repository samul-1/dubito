// to animate card count updates
(function($) {
    $.fn.countTo = function(options) {
        // merge the default plugin settings with the custom options
        options = $.extend({}, $.fn.countTo.defaults, options || {});

        // how many times to update the value, and how much to increment the value on each update
        var loops = Math.ceil(options.speed / options.refreshInterval),
            increment = (options.to - options.from) / loops;

        return $(this).each(function() {
            var _this = this,
                loopCount = 0,
                value = options.from,
                interval = setInterval(updateTimer, options.refreshInterval);

            function updateTimer() {
                value += increment;
                loopCount++;
                $(_this).html(value.toFixed(options.decimals));

                if (typeof(options.onUpdate) == 'function') {
                    options.onUpdate.call(_this, value);
                }

                if (loopCount >= loops) {
                    clearInterval(interval);
                    value = options.to;

                    if (typeof(options.onComplete) == 'function') {
                        options.onComplete.call(_this, value);
                    }
                }
            }
        });
    };

    $.fn.countTo.defaults = {
        from: 0,  // the number the element should start at
        to: 100,  // the number the element should end at
        speed: 1000,  // how long it should take to count between the target numbers
        refreshInterval: 100,  // how often the element should be updated
        decimals: 0,  // the number of decimal places to show
        onUpdate: null,  // callback method for every time the element is updated,
        onComplete: null,  // callback method for when the element finishes updating
    };
})(jQuery);

bind_event_listeners = function() {
    /* this function toggles cards in and out of the array of cards to be put down upon clicking
       and also takes care of toggling the selected class on and off for them */
    $(".selectable_card").click(function () {
        $(this).toggleClass("selected") // toggle selected class when clicked
        // add/remove to list of cards to put down
        this_card_id = $(this).attr('id')
        this_card_class = document.getElementById(this_card_id).classList[0] // first class of the element is card number and seed
        
        idx = selected_cards_id.indexOf(this_card_id) // search for card id in array of selected cards
        if(idx == -1) { // card is not in selected list: add it to the list
            selected_cards_id.push(this_card_id)
            cards_to_put_down.push(this_card_class)
        } else {
            selected_cards_id.splice(idx, 1)
            idx2 = cards_to_put_down.indexOf(this_card_class) // get position of card to remove in cards_to_put_down_array
            cards_to_put_down.splice(idx2, 1) // and remove it
        }
        document.getElementById("n_selected_cards").innerHTML = selected_cards_id.length
        // if(!selected_cards_id.length || turn != my_player_num) {
        //     document.getElementById("place").disabled = true
        // } else {
        //     document.getElementById("place").disabled = false
        // }
    })
}


$(document).ready(function () {
    $("#my_cards").sortable()
    $("#stacked_card").flip()
    $('[data-toggle="popover"]').popover({
        html: true,
        animation: false,
        trigger: 'manual',
        template: '<div class="popover shadow-md" role="tooltip"><div class="arrow"></div><div class="popover-body exclamation-point"></div>',
    })
    $('[data-toggle="popover"]').on('shown.bs.popover', function () {
        var $pop = $(this);
        setTimeout(function () {
            $pop.popover('hide');
        }, 4500);
    });
    $("input[name=card-choice]").attr("disabled", true)

    $("input[name=card-choice]").click(function() {
        $("#claimed_choice").removeClass("reminder")
    })
})

// animated text

animate_you_lose_doubt = function() {
    var textWrapper = document.querySelector('.ml3');
    textWrapper.innerHTML = textWrapper.textContent.replace(/\S/g, "<span class='letter'>$&</span>");

    anime.timeline({loop: false})
    .add({
        targets: '.ml3 .letter',
        opacity: [0,1],
        easing: "easeInOutQuad",
        duration: 1000,
        delay: (el, i) => 70 * (i+1)
    })
}

animate_you_win_doubt = function() {
    anime.timeline({loop: false})
  .add({
    targets: '.ml15 .word',
    scale: [14,1],
    opacity: [0,1],
    easing: "easeOutCirc",
    duration: 800,
    delay: (el, i) => 800 * i
  })
}

animate_neutral_outcome_doubt = function() {
    // Wrap every letter in a span
    var textWrapper = document.querySelector('.ml10 .letters');
    textWrapper.innerHTML = textWrapper.textContent.replace(/\S/g, "<span class='letter'>$&</span>");

anime.timeline({loop: false})
  .add({
    targets: '.ml10 .letter',
    rotateY: [-90, 0],
    duration: 1300,
    delay: (el, i) => 45 * i
  })
}

move_card_to_stack = function(element_id) {
    $("#" + element_id).position({
        my:        "left top",
        at:        "left top",
        of:        $("#card_stack"), // or $("#otherdiv")
        collision: "fit"
    }, 1000)
}

show_placing_animation = function(n) {
    time = 900
    for(let i = 0; i < n; i++) {
        $("#hidden_card").fadeTo(50, 1)
        $("#hidden_card").animate({
            'right' : "25%" //moves right
        }, (min((time/n), 250)), function() {
            $("#hidden_card").fadeTo(0,0); $("#hidden_card").css("right","60%")
        })
    }
        
}

min = function(a, b) {
    if(a >= b)
        return b
    return a
}

animate_begin_round = function() {
    $("#card_choice_modal").modal("show")
    setTimeout(function() {
        if(last_card != -1) {
            $("#c_" + parseInt(last_card)).prop("disabled", "true")
        } else console.log("l" + last_card)
    }, 100)
    // Wrap every letter in a span
    var textWrapper = document.querySelector('.ml1 .letters');
    textWrapper.innerHTML = textWrapper.textContent.replace(/\S/g, "<span class='letter'>$&</span>");

    anime.timeline({loop: false})
    .add({
        targets: '.ml1 .letter',
        scale: [0.3,1],
        opacity: [0,1],
        translateZ: 0,
        easing: "easeOutExpo",
        duration: 300,
        delay: (el, i) => 30 * (i+1)
    }).add({
        targets: '.ml1 .line',
        scaleX: [0,1],
        opacity: [0.5,1],
        easing: "easeOutExpo",
        duration: 300,
        offset: '-=875',
        delay: (el, i, l) => 80 * (l - i)
    })
    $("#claimed_choice").addClass("reminder")
    $("input[name=card-choice]").attr("disabled", false)
    setTimeout(function() {$("#card_choice_modal").modal("hide")}, 2500)
}

sort_cards = function() {
    var toSort = document.getElementById('my_cards').children;
    toSort = Array.prototype.slice.call(toSort, 0);

    toSort.sort(function(a, b) {
        if(a.classList[0][0] == '1') {
            var aord = parseInt(a.classList[0][0] + a.classList[0][1])
        } else {
            var aord = parseInt(a.classList[0][0])
        }

        if(b.classList[0][0] == '1') {
            var bord = parseInt(b.classList[0][0] + b.classList[0][1])
        } else {
            var bord = parseInt(b.classList[0][0])
        }
        // two elements never have the same ID hence this is sufficient:
        return (aord > bord) ? 1 : -1;
    });

    var parent = document.getElementById('my_cards');
    parent.innerHTML = "";

    for(var i = 0, l = toSort.length; i < l; i++) {
        parent.appendChild(toSort[i]);
    }
}