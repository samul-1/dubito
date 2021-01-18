const ws_scheme = window.location.protocol == "https:" ? "wss" : "ws"
const socket = new WebSocket(
    ws_scheme +
    '://' +
    window.location.host +
    '/ws/matchmaking/'
)

let vue = new Vue({
    el: '#app',
    delimiters: ['${', '}'],
    components: {

    },
    data: {
        socket: undefined,
        player_name: '',
        timer: 10,
        timer_started: false,
        game_id: undefined,
        player_found: false,
        searching: false,
        ellipsis: '&nbsp;&nbsp;&nbsp;',
        matchmaking_errors: [],
        handle: null,
        online_players: false,
    },
  
    mounted() {
        const self = this
        socket.onmessage = function (e) {
            data = JSON.parse(e.data)
            // console.log(data)
            switch(data.type) {
            case 'player_found':
                self.game_id = data.game_id
                // self.show_player_joined()
                if(!self.timer_started) {
                    self.player_found = true
                    self.trigger_timer()
                }
                break
            case 'reset_timer':
                self.game_id = null
                self.player_found = false
                clearInterval(self.handle)
                this.handle = null
                self.timer = 10
                self.timer_started = false
                break
            case 'online_players':
                self.online_players = data.value
                break
            }

        }
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

            socket.send(
                JSON.stringify({
                  'type': 'join_matchmaking',
                  'player_name': this.player_name,
                })
            )

            this.searching = true
            this.animateEllipsis()
        },

        trigger_timer() {
            this.timer_started = true
            this.handle = setInterval(() => {
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
