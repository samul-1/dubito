const ws_scheme = window.location.protocol == "https:" ? "wss" : "ws"

const gameSocket = new WebSocket(
    ws_scheme +
    '://'
    + window.location.host
    + '/ws/play/'
    + game_id
    + '/'
)

Vue.component('animated-integer', {
    template: '<span>{{ tweeningValue }}</span>',
    props: {
      value: {
        type: Number,
        required: true
      }
    },
    data: function() {
      return {
        tweeningValue: 0
      }
    },
    watch: {
      value: function(newValue, oldValue) {
        this.tween(oldValue, newValue)
      }
    },
    mounted: function() {
      this.tween(0, this.value)
    },
    methods: {
      tween: function(startValue, endValue) {
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
          .onUpdate(function() {
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
        data: {
            won_by: '',
            reactions_enabled: true,
            outcome_text: '',
            uncovered_stack: [],
            claimed: '',
            selected_cards: [],
            texts: Array(10).fill(""),
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
            },
            state_buffer: {}
        },

        mounted() {
          this.$root.$on('bv::popover::shown', bvEventObj => { // close shown popovers after 4 seconds
            self = this
            setTimeout(function() {
              self.$root.$emit('bv::hide::popover', bvEventObj.target.id)
            }, 4000)
          })
        },

        created() {
            const self = this
            gameSocket.onmessage = function(e) {
                data = JSON.parse(e.data)
                // transfer received state to buffer
                self.state_buffer = data.state
                event_type = data.event_specifics.type
                switch(event_type) {
                    case "round_start":
                    case "cards_placed":
                      self.show_placing_animation(data.event_specifics.number_of_cards_placed) // show cards going to the stack
                      self.copy_buffer_to_state()
                      if(data.event_specifics.by_who != data.my_player_number) {
                        self.set_player_text(data.event_specifics.by_who, false, 
                          data.event_specifics.number_of_cards_placed + 
                          ` <img class="card_icon" src="` + 
                          self.get_card_icon_url(data.state.current_card) + 
                          `" />!`
                        )
                      }
                      break
                    case "doubt":
                      if(data.event_specifics.who_doubted_number != data.my_player_number) {
                        self.set_player_text(data.event_specifics.who_doubted_number, false, "Dubito!")
                      }
                      self.uncovered_stack = data.event_specifics.whole_stack
                      self.reveal_stack(data.event_specifics.whole_stack, self.state.last_amount_played, data.event_specifics.outcome, data.event_specifics.who_doubted)
                      break
                    case "pass_turn":
                    case "player_joined":
                    case "player_disconnected":
                      self.copy_buffer_to_state()
                      break
                    case "reaction":
                      self.set_player_text(data.event_specifics.who, true, data.event_specifics.reaction)
                      break
                    case "player_won":
                      self.won_by = data.event_specifics.winner
                      self.throw_confetti()
                      break
                }
            }
        },

        watch: {
          reactions_enabled: function(new_value) { // re-enables reaction buttons after 4 seconds when they are disabled
            if(!new_value) {
              self = this
              setTimeout(function() {
                self.reactions_enabled = true
              }, 4500)
            }
          },

          number_of_stacked_cards: function(new_value) { // when it's my turn and there are no stacked cards, play begin round animation
            if(!new_value && this.state.my_player_number == this.state.current_turn) {
              $("#card_choice_modal").modal("show")

              this.animate_text()
              setTimeout(function() {
                $("#card_choice_modal").modal("hide")
              }, 2500)
            }
          },
        },

        methods: {
            async throw_confetti() { // throws confetti when a player wins
              for(i = 0; i < 3; i++) {
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
              if(!is_emoji) {
                str = text_or_emoji
              } else {
                str = "<img class='animated_emoji' src='" + static_path + "img/emojis/" + text_or_emoji + ".gif' />"
              }
              Vue.set(this.texts, number, str) // setting the new text this way will make it reactive
              
              idx_str = number + '_popover'
              this.$root.$emit('bv::show::popover', idx_str)
            },

            get_card_strings_from_object(obj) { // used to extract an array containing only the names of the cards from array of objects selected_cards
              array = []
              for(card of obj) {
                array.push(card.card)
              }
              return array
            },

            async reveal_stack(stack, cards_to_flip, outcome, doubter) { // show an animation of cards being flipped for each card the last player put down, then call method reveal the modal
              stacked_back = document.getElementById("stacked_back")
              stacked_front = document.getElementById("stacked_front")
              for(let i = 0; i < cards_to_flip; i++) {
                  this_card = stack[stack.length-i-1]
                  stacked_back.src = static_path_to_card_img + this_card + ".png"
                  j = 0 // used to prevent doubling of post-flipping function when card is flipped back
                  $("#stacked_card").on("flip:done", function(){
                      if(j%2) return
                      j++
                      $("#stacked_card").animate({
                          "right" : "0" //moves right
                      }, 200, function() {
                          $("#hidden_uncovered_card_div").fadeIn(0)
                          document.getElementById("hidden_uncovered_card").src = static_path_to_card_img + this_card + ".png" 
                          $("#stacked_card").fadeOut(0,0);
                          $("#stacked_card").css("right","35%")
                          $("#stacked_card").flip(false)
                      })
                  })
                  $("#stacked_card").fadeIn(0);
                  $("#stacked_card").flip(true)
                  await new Promise(r => setTimeout(r, 1000));
                }
                this.show_stack_modal(outcome, doubter)
            },

            show_stack_modal(outcome, doubter) { // make the modal visible and set a timeout to hide it automatically
              self = this
              if(outcome) {
                this.outcome_text = doubter + " ha dubitato correttamente!"
              } else {
                this.outcome_text = doubter + " ha sbagliato!"
              }

              $("#stack_modal").modal("show")
              $(".card-grid").flip()
              $(".flip_card").flip()
              setTimeout(function() {
                $(".flip_card").flip("true")
              }, 500)
              setTimeout(function() {
                $("#stack_modal").modal("hide")
                $("#hidden_uncovered_card").attr("src", "")
                self.copy_buffer_to_state()
                self.uncovered_stack = []
              }, 1500+(250*this.stack_length))
            },

            show_placing_animation(n) { // show n cards being put on the stack
              time = 900
              for(let i = 0; i < n; i++) {
                  $("#hidden_card").fadeTo(50, 1)
                  $("#hidden_card").animate({
                      'right' : "35%" // moves right
                  }, (this.min((time/n), 250)), function() {
                      $("#hidden_card").fadeTo(0,0); $("#hidden_card").css("right","72.5%")
                  })
              }
            },

            min(a, b) {
              if(a >= b)
                  return b
              return a
            },

            get_card_url(card) { // returns the path to a card image given its number and seed
                return static_path_to_card_img + card + ".png"
            },

            get_card_icon_url(card) { // returns the path to the icon of a card given its number
              return static_path_to_card_img + "icon-" + card + ".png"
            },

            copy_buffer_to_state() { // copies new state received from server from buffer to actual state object
                this.state = this.state_buffer
            },

            toggle_card_selection(card) { // toggles clicked card in and out of selection
                if(this.selected_cards.find(c => c.card === card.card && c.deck === card.deck)) { // if card was selected, remove it from selection list
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

            place_cards() { // sends message to websocket that selected_cards were placed down
              cards = this.get_card_strings_from_object(this.selected_cards)
              gameSocket.send(
                JSON.stringify({
                  'type': 'place_cards',
                  'cards': cards,
                })
              )
              this.selected_cards = []
            },

            start_round() { // sends message to websocket that round started
              if(typeof($("input[name=card-choice]:checked").val()) == "undefined") {
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

            animate_text() {
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
          },
        },
        
        computed: {
          fixed_cards() { // runs through my_cards and attaches a deck number to cards with equal number and seed to distinguish between them when selected; returns the array sorted
            check_cards = []
            this.state.my_cards.forEach(card => {
              let duplicates_count = check_cards.filter(c => c.card === card).length
              check_cards.push({ card: card, deck: duplicates_count + 1 })
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
            if(idx != -1)
              return 'È il turno di ' + this.state.other_players_data[idx].name
            return 'È il mio turno'
          },

          number_of_stacked_cards() {
            return this.state.number_of_stacked_cards
          }
        }
    })