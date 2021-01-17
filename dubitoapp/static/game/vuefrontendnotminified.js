const ws_scheme = window.location.protocol == "https:" ? "wss" : "ws"

const gameSocket = new WebSocket(
  ws_scheme +
  '://' +
  window.location.host +
  '/ws/play/' +
  game_id +
  '/'
)

// progressive image component


// tweening value component
Vue.component('animated-integer', {
  template: '<span>{{ tweeningValue }}</span>',
  props: {
    value: {
      type: Number,
      required: true
    }
  },
  data: function () {
    return {
      tweeningValue: 0
    }
  },
  watch: {
    value: function (newValue, oldValue) {
      this.tween(oldValue, newValue)
    }
  },
  mounted: function () {
    this.tween(0, this.value)
  },
  methods: {
    tween: function (startValue, endValue) {
      var vm = this

      function animate() {
        if (TWEEN.update()) {
          requestAnimationFrame(animate)
        }
      }
      new TWEEN.Tween({
          tweeningValue: startValue
        })
        .to({
          tweeningValue: endValue
        }, 500)
        .onUpdate(function () {
          vm.tweeningValue = this.tweeningValue.toFixed(0)
        })
        .start()
      animate()
    }
  }
})

let vue = new Vue({
  el: '#app',
  delimiters: ['${', '}'],
  components: {
    ProgressiveImage: window.VueProgressiveImage,
  },
  data: {
    mobile_chat_opened: false,
    restarted_by: -1,
    restarted_by_name: '',
    chat_input: '',
    progressively_fired: false,
    won_by: '',
    reactions_enabled: true,
    chat_enabled: true,
    outcome_text: '',
    removed_cards_text: '',
    uncovered_stack: [],
    claimed: '',
    selected_cards: [],
    win_buffer: '',
    texts: Array(10).fill(""),
    playing_animation: false,
    open_popovers: [],
    state: {
      current_turn: 0,
      last_turn: -1,
      current_card: 0,
      last_card: -1,
      number_of_stacked_cards: 0.5, // non-integer default value to prevent animated_integer component from showing it
      last_amount_played: 0,
      won_by: -1,
      my_cards: [],
      other_players_data: [],
      my_player_number: -1,
      all_players_joined: 0,
    },
    state_buffer: {}
  },

  mounted() {
    this.$root.$on('bv::popover::show', bvEventObj => { // close shown popovers after 4 seconds
      // console.log(bvEventObj)
        self = this
      // create reference to new closure timeout
      let ref = {component: bvEventObj.target.id}
      // schedule event to close the popover
      handle = setTimeout(function () {
        self.$root.$emit('bv::hide::popover', bvEventObj.target.id)
      }, 4000)
      ref.handle = handle
      this.open_popovers.push(ref) // pushes reference to this popover onto open_popovers
    })
    setInterval(window.progressively.init, 2000)
  },

  created() {
    const self = this
    gameSocket.onmessage = function (e) {
      data = JSON.parse(e.data)
      // console.log(data)
      // transfer received state to buffer
      event_type = data.event_specifics.type
      if(event_type != "reaction" && event_type != "message" && event_type != "restart") {
        self.state_buffer = data.state
      }
      switch (event_type) {
        case "round_start":
        case "cards_placed":
          self.show_placing_animation(data.event_specifics.number_of_cards_placed) // show cards going to the stack
          self.copy_buffer_to_state()
          if (data.event_specifics.by_who != data.my_player_number) {
            self.set_player_text(data.event_specifics.by_who, false,
              data.event_specifics.number_of_cards_placed +
              ` <img class="card_icon" src="` +
              self.get_card_icon_url(data.state.current_card) +
              `" />!`
            )
          }
          break
        case "doubt":
          // console.log(data.event_specifics)
          if (data.event_specifics.who_doubted_number != data.my_player_number) {
            self.set_player_text(data.event_specifics.who_doubted_number, false, window.gettext("Dubito!"))
          }
          surprise_sound.play()
          self.uncovered_stack = data.event_specifics.whole_stack
          self.reveal_stack(
            data.event_specifics.whole_stack,
            self.state.last_amount_played,
            data.event_specifics.outcome,
            data.event_specifics.who_doubted,
            data.event_specifics.copies_removed,
            data.event_specifics.losing_player
            )
          self.selected_cards = []
          break
        case "pass_turn":
        case "player_joined":
        case "player_disconnected":
          self.copy_buffer_to_state()
          break
        case "reaction":
          self.set_player_text(data.event_specifics.who, true, data.event_specifics.reaction)
          break
        case "message":
            self.set_player_text(data.event_specifics.who, false, data.event_specifics.message)
            break
        case "player_won":
          self.win_buffer = data.event_specifics.winner
          // self.won_by = data.event_specifics.winner
          // self.throw_confetti()
          break
        case "restart":
          self.restart_routine(data.event_specifics.by)
          break
      }
      if(!self.progressively_fired) {
          setTimeout(function(s) {
            window.progressively.init({
              onLoadComplete: function() {
                self.progressively_fired = true
              },
            })
          }, 100)
        //self.progressively_fired = true
      }
    }
  },

  watch: {
    reactions_enabled: function (new_value) { // re-enables reaction buttons after 4.5 seconds when they are disabled
      if (!new_value) {
        self = this
        setTimeout(function () {
          self.reactions_enabled = true
        }, 4500)
      }
    },

    chat_enabled: function (new_value) { // re-enables chat after 2.5 seconds when it's disabled
        if (!new_value) {
          self = this
          setTimeout(function () {
            self.chat_enabled = true
          }, 2500)
        }
      },

    number_of_stacked_cards: function (new_value) { // when it's my turn and there are no stacked cards, play begin round animation
      if (!new_value && this.state.my_player_number == this.state.current_turn) {
        $("#card_choice_modal").modal("show")

        this.animate_text()
        setTimeout(function () {
          $("#card_choice_modal").modal("hide")
        }, 2500)
      }
    },
  },

  methods: {
    async throw_confetti() { // throws confetti when a player wins
      clapping_sound.play()
      for (i = 0; i < 3; i++) {
        confetti({
          particleCount: 280,
          startVelocity: 25,
          spread: 330,
          origin: {
            x: 0.1,
            y: 0.35
          }
        })
        await new Promise(r => setTimeout(r, 300));
        confetti({
          particleCount: 300,
          startVelocity: 25,
          spread: 360,
          origin: {
            x: 0.5,
            y: 0.35
          }
        })
        await new Promise(r => setTimeout(r, 300));
        confetti({
          particleCount: 280,
          startVelocity: 25,
          spread: 330,
          origin: {
            x: 0.9,
            y: 0.35
          }
        })
        await new Promise(r => setTimeout(r, 1000));
      }
    },

    set_player_text(number, is_emoji, text_or_emoji) { // sets player text to given value, shows relevant popover, and triggers the event that after 4 seconds will hide it
      let idx = this.state.other_players_data.findIndex(p => p.number === number)
      if (!is_emoji) {
        str = text_or_emoji
      } else {
        str = "<img class='animated_emoji' src='" + static_path + "img/emojis/" + text_or_emoji + ".gif' />"
      }
      Vue.set(this.texts, number, str) // setting the new text this way will make it reactive

      idx_str = number + '_popover'
      
      // if player has a popover already shown, reset its hide timer
    //   let open = this.open_popovers.findIndex(p => p.component === idx_str)
    //   // console.log(idx_str)

    //   if(open != -1) {
    //     window.clearTimeout(this.open_popovers[open].handle)
    //     this.open_popovers[open].handle = setTimeout(function () {
    //       self.$root.$emit('bv::hide::popover', idx_str)
    //     }, 4000)
    //     this.open_popovers.splice(open, 1)
    //   } 
      this.$root.$emit('bv::show::popover', idx_str)
    },

    get_card_strings_from_object(obj) { // used to extract an array containing only the names of the cards from array of objects selected_cards
      array = []
      for (card of obj) {
        array.push(card.card)
      }
      return array
    },

    // show an animation of cards being flipped for each card the last player put down, then call method reveal the modal
    async reveal_stack(stack, cards_to_flip, outcome, doubter, copies_removed, losing_player) {
      this.playing_animation = true
      stacked_back = document.getElementById("stacked_back")
      stacked_front = document.getElementById("stacked_front")
      self = this
      // for each card, flip it and move to the right
      for (let i = 0; i < cards_to_flip; i++) {
        this_card = stack[stack.length - i - 1]
        stacked_back.src = self.get_card_url(this_card) // static_path_to_card_img + this_card + ".png"
        j = 0 // used to prevent doubling of post-flipping function when card is flipped back
        flipped_sound.play()
        $("#stacked_card").on("flip:done", function () {
          if (j % 2) return
          j++
          $("#stacked_card").animate({
            "right": hiddenUncoveredCardPosition //moves right
          }, 200, function () {
            $("#hidden_uncovered_card_div").fadeIn(0)
            document.getElementById("hidden_uncovered_card").src = self.get_card_url(this_card) //static_path_to_card_img + this_card + "-min.png"
            $("#stacked_card").fadeOut(0, 0);
            $("#stacked_card").css("right", stackPosition)
            $("#stacked_card").flip(false)
          })
        })
        $("#stacked_card").fadeIn(0);
        $("#stacked_card").flip(true)
        await new Promise(r => setTimeout(r, 1000));
      }
      // call function that will show modal and, afterwards, show cards being discarded if there are 8 copies of them in player's hand
      this.play_copies_removed_animation(outcome, doubter, copies_removed, losing_player)
      this.playing_animation = false
    },

    // make the modal visible and set a timeout to hide it automatically
    async show_stack_modal(outcome, doubter) {
      if (outcome) {
        this.outcome_text = doubter + " " + window.gettext("ha dubitato correttamente") + "!"
        success_sound.play()
      } else {
        this.outcome_text = doubter + " " + window.gettext("ha sbagliato") + "!"
        failure_sound.play()
      }

      $("#stack_modal").modal("show")
      $(".card-grid").flip()
      $(".flip_card").flip()
      setTimeout(function () {
        $(".flip_card").flip(true)
      }, 500)
      await new Promise(r => setTimeout(r, 1500 + (250 * this.stack_length)));
     
      $("#stack_modal").modal("hide")
      $("#hidden_uncovered_card").attr("src", this.get_card_icon_url(0))
    },

    // call show_stack_modal and afterwards, if player has 8 copies of a card, show animation of them being removed
    // show_stack_modal needs to be called first and awaited so that this animation can play once the previous has finished
    async play_copies_removed_animation(outcome, doubter, removed_cards, losing_player) {
      await this.show_stack_modal(outcome, doubter)
      self = this
      if(!removed_cards.length) {
        self.copy_buffer_to_state()
        self.uncovered_stack = []
        return
      }
      this.outcome_text = ""
      this.removed_cards_text = losing_player + " " + window.gettext("ha tutte e 8 le copie di ") + "<img class='card_icon' src='" + this.get_card_icon_url(removed_cards[0]) + "' />, " + window.gettext("quindi le scarta")
      this.uncovered_stack = this.get_eight_copies_of(removed_cards[0]) //.push(removed_cards[0] + "D")
      $("#stack_modal").modal("show")
      setTimeout(function () { // enable flipping
        $(".card-grid").flip()
        $(".flip_card").flip()
        $(".flip_card").flip(true)
        setTimeout(function () { // flip removed cards
          $(".flip_card").flip(false)
          setTimeout(function() { // fade out removed cards
            $(".flip_card").fadeTo(100, 0)
          }, 800)
        }, 1500)
      }, 0)
      setTimeout(function () { // hide modal, empty stack, and copy new game state from buffer
        $("#stack_modal").modal("hide")
        self.removed_cards_text = ""
        self.copy_buffer_to_state()
        self.uncovered_stack = []
      }, 2500)
    },

    show_placing_animation(n) { // show n cards being put on the stack
      this.playing_animation = true // disable buttons during animation
      time = 900
      let i
      for (i = 0; i < n; i++) {
        $("#hidden_card").fadeTo(50, 1)
        $("#hidden_card").animate({
          'right': stackPosition // moves right
        }, (this.min((time / n), 250)), () => {
          $("#hidden_card").fadeTo(0, 0);
          $("#hidden_card").css("right", hiddenCardPosition)
          placed_sound.cloneNode(true).play()
          if(i == (n-1)) this.playing_animation = false 
        })
      }
      // re-enable buttons when done with animation
      setTimeout(() => { this.playing_animation = false }, this.min((time / n), 250))
    },

    min(a, b) {
      if (a >= b)
        return b
      return a
    },

    get_card_url(card) { // returns the path to a card image given its number and seed
      return static_path_to_card_img + card + "-min.png"
    },

    get_card_icon_url(card) { // returns the path to the icon of a card given its number
      return static_path_to_card_img + "icon-" + card + "-min.png"
    },

    copy_buffer_to_state() { // copies new state received from server from buffer to actual state object
      if(this.win_buffer) {
        if(this.won_by == '') {
          this.throw_confetti()
        }
        this.won_by = this.win_buffer
      } else {
        this.state = this.state_buffer
      }
    },

    toggle_card_selection(card) { // toggles clicked card in and out of selection
      if (this.selected_cards.find(c => c.card === card.card && c.deck === card.deck)) { // if card was selected, remove it from selection list
        this.selected_cards.splice(this.selected_cards.findIndex(c => c.card === card.card && c.deck === card.deck), 1)
      } else { // otherwise add it to the list
        this.selected_cards.push(card)
      }
    },

    send_reaction(emoji) { // sends message to websocket to broadcast the reaction emoji specified in the argument
      gameSocket.send(
        JSON.stringify({
          'type': 'reaction',
          'reaction': emoji,
        })
      )
      this.reactions_enabled = false // watcher will re-enable the buttons after 4 seconds
    },

    place_cards(placing_lots_of_cards) { // sends message to websocket that selected_cards were placed down
      if(placing_lots_of_cards) {
        if(!confirm(window.gettext("Hai selezionato la bellezza di ") + this.number_of_selected_cards + window.gettext(" carte. Sei sicuro di volerle mettere giù?"))) {
          return
        }
      }
      cards = this.get_card_strings_from_object(this.selected_cards)
      gameSocket.send(
        JSON.stringify({
          'type': 'place_cards',
          'cards': cards,
        })
      )
      this.selected_cards = []
    },

    send_chat_message() { // sends a chat message to websocket
        if(!this.chat_enabled) {
            return
        }
        gameSocket.send(
            JSON.stringify({
                'type': 'chat_message',
                'message': this.chat_input,
            })
        )
        this.chat_input = ''
        this.chat_enabled = false // watcher will re-enable chat after 4 seconds
    },

    start_round() { // sends message to websocket that round started
      if (typeof ($("input[name=card-choice]:checked").val()) == "undefined") {
        $(".reminder").effect("shake")
        return
      }
      cards = this.get_card_strings_from_object(this.selected_cards)
      gameSocket.send(
        JSON.stringify({
          'type': 'start_round',
          'cards': cards,
          'claimed': $("input[name=card-choice]:checked").val(),
        })
      )
      this.claimed = ''
      this.selected_cards = []
    },

    doubt() { // sends message to websocket that you doubted
      gameSocket.send(
        JSON.stringify({
          'type': 'doubt',
        })
      )
    },

    restart_game() { // sends message to websocket to restart ended game
      gameSocket.send(
        JSON.stringify({
          'type': 'restart',
        })
      )
    },

    restart_routine(restarted_by) { // called upon receiving message from websocket that somebody wants to play again      
      let idx = this.state.other_players_data.findIndex(p => p.number === restarted_by)
      if (idx != -1) {
        this.restarted_by = restarted_by
        this.restarted_by_name = this.state.other_players_data[idx].name
      } else {
        // reload page and to begin playing new game
        window.location.reload()
      }
    },

    animate_text() {
      // Wrap every letter in a span
      var textWrapper = document.querySelector('.ml1 .letters');
      textWrapper.innerHTML = textWrapper.textContent.replace(/\S/g, "<span class='letter'>$&</span>");

      anime.timeline({
          loop: false
        })
        .add({
          targets: '.ml1 .letter',
          scale: [0.3, 1],
          opacity: [0, 1],
          translateZ: 0,
          easing: "easeOutExpo",
          duration: 300,
          delay: (el, i) => 30 * (i + 1)
        }).add({
          targets: '.ml1 .line',
          scaleX: [0, 1],
          opacity: [0.5, 1],
          easing: "easeOutExpo",
          duration: 300,
          offset: '-=875',
          delay: (el, i, l) => 80 * (l - i)
        })
    },

    get_eight_copies_of(card) { // gets an array containing 8 copies of given card of all seeds in random order
      /* Randomize array in-place using Durstenfeld shuffle algorithm */
      function shuffleArray(array) {
        for (var i = array.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1))
            var temp = array[i]
            array[i] = array[j]
            array[j] = temp
        }
      }
      let res = []
      let seeds = ['D','D','H','H','S','S','C','C']
      shuffleArray(seeds)
      for(let i = 0; i < 7; i++) {
        res.push(card + seeds[i])
      }
      return res
    }
  },

  computed: {
    fixed_cards() { // runs through my_cards and attaches a deck number to cards with equal number and seed to distinguish between them when selected; returns the array sorted
      check_cards = []
      this.state.my_cards.forEach(card => {
        let duplicates_count = check_cards.filter(c => c.card === card).length
        check_cards.push({
          card: card,
          deck: duplicates_count + 1
        })
      })

      function comp(a, b) {
        return parseInt(a.card) - parseInt(b.card)
      }
      return check_cards.sort(comp)
    },

    number_of_selected_cards() {
      return this.selected_cards.length
    },

    stack_length() {
      return this.uncovered_stack.length
    },

    current_turn() {
      return this.state.current_turn
    },

    current_turn_name() {
      let idx = this.state.other_players_data.findIndex(p => p.number === this.state.current_turn)
      if (idx != -1) {
        const format = window.gettext('È il turno di %s')
        return interpolate(format, [this.state.other_players_data[idx].name])
      }
        // return 'È il turno di ' + this.state.other_players_data[idx].name
      return window.gettext('È il mio turno')
    },

    number_of_stacked_cards() {
      return this.state.number_of_stacked_cards
    }
  }
})
