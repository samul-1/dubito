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
            drag: false,
            uncovered_stack: [],
            claimed: '',
            selected_cards: [],
            state: {
                current_turn: 0,
                last_turn: -1,
                current_card: 0,
                last_card: -1,
                number_of_stacked_cards: 0,
                last_amount_played: 0,
                won_by: -1,
                my_cards: [],
                other_players_data: {},
            },
            state_buffer: {}
        },

        created() {
            const self = this
            gameSocket.onmessage = function(e) {
                data = JSON.parse(e.data)
                // transfer received state to buffer
                self.state_buffer = data.state

                event_type = data.event_specifics.type
                console.log("old state")
                console.log(self.state)
                console.log(event_type)
                switch(event_type) {
                    case "round_start":
                    case "cards_placed":
                      self.show_placing_animation(data.event_specifics.number_of_cards_placed) // show cards going to the stack
                      self.copy_buffer_to_state()
                      break
                    case "doubt":
                      self.uncovered_stack = data.event_specifics.whole_stack
                      self.reveal_stack(data.event_specifics.whole_stack, self.state.last_amount_played)
                      break
                    case "player_joined":
                      self.copy_buffer_to_state()
                      break
                }
                console.log("new state")
                console.log(self.state)
            }
        },

        watch: {
        },

        methods: {
            get_card_strings_from_object(obj) {
              array = []
              for(card of obj) {
                array.push(card.card)
              }
              console.log(array)
              return array
            },

            async reveal_stack(stack, cards_to_flip) {
              stacked_back = document.getElementById("stacked_back")
              stacked_front = document.getElementById("stacked_front")
              for(let i = 0; i < cards_to_flip; i++) {
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
                this.show_stack_modal()
                this.copy_buffer_to_state()
            },

            show_stack_modal() {
              $("#stack_modal").modal("show")
              $(".card-grid").flip()
              $(".flip_card").flip()
              setTimeout(function() {
                $(".flip_card").flip("toggle")
              }, 500)
              setTimeout(function() {
                $("#stack_modal").modal("hide")
                $("#hidden_uncovered_card").attr("src", "")
              }, 1500+(250*this.stack_length))
            },

            show_placing_animation(n) {
              time = 900
              for(let i = 0; i < n; i++) {
                  $("#hidden_card").fadeTo(50, 1)
                  $("#hidden_card").animate({
                      'right' : "25%" // moves right
                  }, (this.min((time/n), 250)), function() {
                      $("#hidden_card").fadeTo(0,0); $("#hidden_card").css("right","60%")
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

            get_card_icon_url(card) {
              return static_path_to_card_img + "icon-" + card + ".png"
            },

            copy_buffer_to_state() {
                this.state = this.state_buffer
            },

            toggle_card_selection(card) {
                if(this.selected_cards.find(c => c.card === card.card && c.deck === card.deck)) { // if card was selected, remove it from selection list
                    this.selected_cards.splice(this.selected_cards.indexOf(card), 1)
                } else { // otherwise add it to the list
                    this.selected_cards.push(card)
                }
            },

            place_cards() { // sends message to websocket that selected_cards were placed down
              console.log("place_cards")
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
              console.log("start_round")
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

            sort_cards() {
                function comp(a, b) {
                    return parseInt(a) - parseInt(b)
                }
                this.state.my_cards.sort(comp)
            },
        },
        
        computed: {
          fixed_cards() {
            check_cards = []
            this.state.my_cards.forEach(card => {
              let duplicates_count = check_cards.filter(c => c.card === card).length
              check_cards.push({ card: card, deck: duplicates_count + 1 })
            })
            return check_cards
          },
          // fixed_cards() {
          //   check_cards = []
          //   this.state.my_cards.forEach(card => {
          //     if(check_cards.find(c => c.card === card)) {
          //       check_cards.push({ card: card, deck: 2 })
          //     } else {
          //       check_cards.push({ card: card, deck: 1 })
          //     }
          //   })
          //   return check_cards
          // },

          number_of_selected_cards() {
              return this.selected_cards.length
          },

          stack_length() {
            return this.uncovered_stack.length
          },

          current_turn_player_name() {
          },
        }

    })