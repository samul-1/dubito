
let vue = new Vue({
    el: '#app',
    delimiters: ['${', '}'],
    components: {

    },
    data: {
        socket: undefined,
        ws_scheme: window.location.protocol == "https:" ? "wss" : "ws",
        player_name: '',
        timer: 10,
        timer_started: false,
        game_id: undefined,
        player_found: false,
        searching: false,
        ellipsis: '&nbsp;&nbsp;&nbsp;',
        matchmaking_errors: [],
    },
  
    mounted() {

    },
  
    created() {
    },
  
    watch: {
      
    },
  
    methods: {
        enter_matchmaking() {
            this.matchmaking_errors = []

            if(!this.player_name.length) {
                this.matchmaking_errors.push(window.gettext("Campo richiesto."))
                return
            }
            if(!/^[a-z0-9]+$/i.test(this.player_name)) {
                this.matchmaking_errors.push(window.gettext("Il tuo nome contiene caratteri non consentiti."))
                return
            }

            this.searching = true
            this.animateEllipsis()

            this.socket = new WebSocket(
                this.ws_scheme +
                '://' +
                window.location.host +
                '/ws/matchmaking/' +
                this.player_name +
                '/'
            )
            const self = this
            this.socket.onmessage = function (e) {
              data = JSON.parse(e.data)
              console.log(data)
              switch(data.type) {
                  case 'player_found':
                      self.game_id = data.game_id
                      // self.show_player_joined()
                      if(!self.timer_started) {
                          self.player_found = true
                          self.trigger_timer()
                      }
                      break
              }
            }
        },

        trigger_timer() {
            this.timer_started = true
            setInterval(() => {
                this.timer--
                if(!this.timer) {
                    window.location.href = '/game/game/' + this.game_id
                }
            }, 1000)
        },
        animateEllipsis() {
            let i = 0
        
            setInterval(() => {
                this.ellipsis = this.stringTimes('.', (i++)%4, 3)
            }, 400)
        },

        stringTimes(str, times, max) {
            let res = ''
            for(let i = 0; i < times; i++) {
                res += str
            }
            for(let i = times; i < max; i++) {
                res += '&nbsp;'
            }
            return res
        },
    },
    

    computed: {
        seconds() {
            return this.timer != 1 ? window.gettext("secondi") : window.gettext("secondo")
        }
    }
  })
