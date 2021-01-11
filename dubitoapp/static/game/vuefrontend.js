const ws_scheme="https:"==window.location.protocol?"wss":"ws",gameSocket=new WebSocket(ws_scheme+"://"+window.location.host+"/ws/play/"+game_id+"/");Vue.component("animated-integer",{template:"<span>{{ tweeningValue }}</span>",props:{value:{type:Number,required:!0}},data:function(){return{tweeningValue:0}},watch:{value:function(e,t){this.tween(t,e)}},mounted:function(){this.tween(0,this.value)},methods:{tween:function(e,t){var a=this;new TWEEN.Tween({tweeningValue:e}).to({tweeningValue:t},500).onUpdate(function(){a.tweeningValue=this.tweeningValue.toFixed(0)}).start(),function e(){TWEEN.update()&&requestAnimationFrame(e)}()}}});let vue=new Vue({el:"#app",delimiters:["${","}"],components:{ProgressiveImage:window.VueProgressiveImage},data:{mobile_chat_opened:!1,restarted_by:-1,restarted_by_name:"",chat_input:"",progressively_fired:!1,won_by:"",reactions_enabled:!0,chat_enabled:!0,outcome_text:"",removed_cards_text:"",uncovered_stack:[],claimed:"",selected_cards:[],win_buffer:"",texts:Array(10).fill(""),playing_animation:!1,open_popovers:[],state:{current_turn:0,last_turn:-1,current_card:0,last_card:-1,number_of_stacked_cards:.5,last_amount_played:0,won_by:-1,my_cards:[],other_players_data:[],my_player_number:-1,all_players_joined:0},state_buffer:{}},mounted(){this.$root.$on("bv::popover::show",e=>{console.log(e),self=this;let t={component:e.target.id};handle=setTimeout(function(){self.$root.$emit("bv::hide::popover",e.target.id)},4e3),t.handle=handle,this.open_popovers.push(t)}),setInterval(window.progressively.init,2e3)},created(){const e=this;gameSocket.onmessage=function(t){switch(data=JSON.parse(t.data),console.log(data),event_type=data.event_specifics.type,"reaction"!=event_type&&"message"!=event_type&&"restart"!=event_type&&(e.state_buffer=data.state),event_type){case"round_start":case"cards_placed":e.show_placing_animation(data.event_specifics.number_of_cards_placed),e.copy_buffer_to_state(),data.event_specifics.by_who!=data.my_player_number&&e.set_player_text(data.event_specifics.by_who,!1,data.event_specifics.number_of_cards_placed+' <img class="card_icon" src="'+e.get_card_icon_url(data.state.current_card)+'" />!');break;case"doubt":data.event_specifics.who_doubted_number!=data.my_player_number&&e.set_player_text(data.event_specifics.who_doubted_number,!1,"Dubito!"),surprise_sound.play(),e.uncovered_stack=data.event_specifics.whole_stack,e.reveal_stack(data.event_specifics.whole_stack,e.state.last_amount_played,data.event_specifics.outcome,data.event_specifics.who_doubted,data.event_specifics.copies_removed,data.event_specifics.losing_player);break;case"pass_turn":case"player_joined":case"player_disconnected":e.copy_buffer_to_state();break;case"reaction":e.set_player_text(data.event_specifics.who,!0,data.event_specifics.reaction);break;case"message":e.set_player_text(data.event_specifics.who,!1,data.event_specifics.message);break;case"player_won":e.win_buffer=data.event_specifics.winner;break;case"restart":e.restart_routine(data.event_specifics.by)}e.progressively_fired||setTimeout(function(t){window.progressively.init({onLoadComplete:function(){e.progressively_fired=!0}})},100)}},watch:{reactions_enabled:function(e){e||(self=this,setTimeout(function(){self.reactions_enabled=!0},4500))},chat_enabled:function(e){e||(self=this,setTimeout(function(){self.chat_enabled=!0},2500))},number_of_stacked_cards:function(e){e||this.state.my_player_number!=this.state.current_turn||($("#card_choice_modal").modal("show"),this.animate_text(),setTimeout(function(){$("#card_choice_modal").modal("hide")},2500))}},methods:{async throw_confetti(){for(clapping_sound.play(),i=0;i<3;i++)confetti({particleCount:280,startVelocity:25,spread:330,origin:{x:.1,y:.35}}),await new Promise(e=>setTimeout(e,300)),confetti({particleCount:300,startVelocity:25,spread:360,origin:{x:.5,y:.35}}),await new Promise(e=>setTimeout(e,300)),confetti({particleCount:280,startVelocity:25,spread:330,origin:{x:.9,y:.35}}),await new Promise(e=>setTimeout(e,1e3))},set_player_text(e,t,a){this.state.other_players_data.findIndex(t=>t.number===e);str=t?"<img class='animated_emoji' src='"+static_path+"img/emojis/"+a+".gif' />":a,Vue.set(this.texts,e,str),idx_str=e+"_popover";let s=this.open_popovers.findIndex(e=>e.component===idx_str);-1!=s&&(window.clearTimeout(this.open_popovers[s].handle),this.open_popovers[s].handle=setTimeout(function(){self.$root.$emit("bv::hide::popover",idx_str)},4e3),this.open_popovers.splice(s,1)),this.$root.$emit("bv::show::popover",idx_str)},get_card_strings_from_object(e){for(card of(array=[],e))array.push(card.card);return array},async reveal_stack(e,t,a,s,i,r){this.playing_animation=!0,stacked_back=document.getElementById("stacked_back"),stacked_front=document.getElementById("stacked_front"),self=this;for(let a=0;a<t;a++)this_card=e[e.length-a-1],stacked_back.src=self.get_card_url(this_card),j=0,flipped_sound.play(),$("#stacked_card").on("flip:done",function(){j%2||(j++,$("#stacked_card").animate({right:hiddenUncoveredCardPosition},200,function(){$("#hidden_uncovered_card_div").fadeIn(0),document.getElementById("hidden_uncovered_card").src=self.get_card_url(this_card),$("#stacked_card").fadeOut(0,0),$("#stacked_card").css("right",stackPosition),$("#stacked_card").flip(!1)}))}),$("#stacked_card").fadeIn(0),$("#stacked_card").flip(!0),await new Promise(e=>setTimeout(e,1e3));this.play_copies_removed_animation(a,s,i,r),this.playing_animation=!1},async show_stack_modal(e,t){e?(this.outcome_text=t+" "+window.gettext("ha dubitato correttamente")+"!",success_sound.play()):(this.outcome_text=t+" "+window.gettext("ha sbagliato")+"!",failure_sound.play()),$("#stack_modal").modal("show"),$(".card-grid").flip(),$(".flip_card").flip(),setTimeout(function(){$(".flip_card").flip(!0)},500),await new Promise(e=>setTimeout(e,1500+250*this.stack_length)),$("#stack_modal").modal("hide"),$("#hidden_uncovered_card").attr("src",this.get_card_icon_url(0))},async play_copies_removed_animation(e,t,a,s){if(await this.show_stack_modal(e,t),self=this,!a.length)return self.copy_buffer_to_state(),void(self.uncovered_stack=[]);this.outcome_text="",this.removed_cards_text=s+" "+window.gettext("ha tutte e 8 le copie di ")+"<img class='card_icon' src='"+this.get_card_icon_url(a[0])+"' />, "+window.gettext("quindi le scarta"),this.uncovered_stack=this.get_eight_copies_of(a[0]),$("#stack_modal").modal("show"),setTimeout(function(){$(".card-grid").flip(),$(".flip_card").flip(),$(".flip_card").flip(!0),setTimeout(function(){$(".flip_card").flip(!1),setTimeout(function(){$(".flip_card").fadeTo(100,0)},800)},1500)},0),setTimeout(function(){$("#stack_modal").modal("hide"),self.removed_cards_text="",self.copy_buffer_to_state(),self.uncovered_stack=[]},2500)},show_placing_animation(e){let t;for(this.playing_animation=!0,time=900,t=0;t<e;t++)$("#hidden_card").fadeTo(50,1),$("#hidden_card").animate({right:stackPosition},this.min(time/e,250),()=>{$("#hidden_card").fadeTo(0,0),$("#hidden_card").css("right",hiddenCardPosition),placed_sound.cloneNode(!0).play(),t==e-1&&(this.playing_animation=!1)});setTimeout(()=>{this.playing_animation=!1},this.min(time/e,250))},min:(e,t)=>e>=t?t:e,get_card_url:e=>static_path_to_card_img+e+"-min.png",get_card_icon_url:e=>static_path_to_card_img+"icon-"+e+"-min.png",copy_buffer_to_state(){this.win_buffer?(""==this.won_by&&this.throw_confetti(),this.won_by=this.win_buffer):this.state=this.state_buffer},toggle_card_selection(e){this.selected_cards.find(t=>t.card===e.card&&t.deck===e.deck)?this.selected_cards.splice(this.selected_cards.findIndex(t=>t.card===e.card&&t.deck===e.deck),1):this.selected_cards.push(e)},send_reaction(e){gameSocket.send(JSON.stringify({type:"reaction",reaction:e})),this.reactions_enabled=!1},place_cards(e){e&&!confirm(window.gettext("Hai selezionato la bellezza di ")+this.number_of_selected_cards+window.gettext(" carte. Sei sicuro di volerle mettere giù?"))||(cards=this.get_card_strings_from_object(this.selected_cards),gameSocket.send(JSON.stringify({type:"place_cards",cards:cards})),this.selected_cards=[])},send_chat_message(){this.chat_enabled&&(gameSocket.send(JSON.stringify({type:"chat_message",message:this.chat_input})),this.chat_input="",this.chat_enabled=!1)},start_round(){void 0!==$("input[name=card-choice]:checked").val()?(cards=this.get_card_strings_from_object(this.selected_cards),gameSocket.send(JSON.stringify({type:"start_round",cards:cards,claimed:$("input[name=card-choice]:checked").val()})),this.claimed="",this.selected_cards=[]):$(".reminder").effect("shake")},doubt(){gameSocket.send(JSON.stringify({type:"doubt"}))},restart_game(){gameSocket.send(JSON.stringify({type:"restart"}))},restart_routine(e){let t=this.state.other_players_data.findIndex(e=>e.number===this.restarted_by);-1!=t?(this.restarted_by=e,this.restarted_by_name=this.state.other_players_data[t].name):window.location.reload()},animate_text(){var e=document.querySelector(".ml1 .letters");e.innerHTML=e.textContent.replace(/\S/g,"<span class='letter'>$&</span>"),anime.timeline({loop:!1}).add({targets:".ml1 .letter",scale:[.3,1],opacity:[0,1],translateZ:0,easing:"easeOutExpo",duration:300,delay:(e,t)=>30*(t+1)}).add({targets:".ml1 .line",scaleX:[0,1],opacity:[.5,1],easing:"easeOutExpo",duration:300,offset:"-=875",delay:(e,t,a)=>80*(a-t)})},get_eight_copies_of(e){let t=[],a=["D","D","H","H","S","S","C","C"];!function(e){for(var t=e.length-1;t>0;t--){var a=Math.floor(Math.random()*(t+1)),s=e[t];e[t]=e[a],e[a]=s}}(a);for(let s=0;s<7;s++)t.push(e+a[s]);return t}},computed:{fixed_cards(){return check_cards=[],this.state.my_cards.forEach(e=>{let t=check_cards.filter(t=>t.card===e).length;check_cards.push({card:e,deck:t+1})}),check_cards.sort(function(e,t){return parseInt(e.card)-parseInt(t.card)})},number_of_selected_cards(){return this.selected_cards.length},stack_length(){return this.uncovered_stack.length},current_turn(){return this.state.current_turn},current_turn_name(){let e=this.state.other_players_data.findIndex(e=>e.number===this.state.current_turn);if(-1!=e){const t=window.gettext("È il turno di %s");return interpolate(t,[this.state.other_players_data[e].name])}return window.gettext("È il mio turno")},number_of_stacked_cards(){return this.state.number_of_stacked_cards}}});