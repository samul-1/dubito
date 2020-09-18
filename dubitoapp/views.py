from django.shortcuts import render
from .models import Game, Player, CardsInHand
import random
import logging
from django.db.models import Q
from .forms import GameForm, JoinForm

# Create your views here.

from django.http import HttpResponse, HttpResponseRedirect


def index(request):
    return render(request, "index.html")

def get_joined_players(request, game_id):
    try:
        game = Game.objects.get(pk=game_id)
        n = game.joined_players
        return HttpResponse(str(n))
    except:
        return HttpResponse("-1")

def create_new_game(request):    
    if request.method == "POST":
        form = GameForm(request.POST)

        if form.is_valid():
            number_of_players = form.cleaned_data["number_of_players"]
            logging.warning(number_of_players)
            game_code = random.randint(10000, 99999) # generate random gamecode

            new_game = Game()
            new_game.number_of_players = number_of_players
            new_game.code = game_code
            new_game.player_current_turn = random.randint(1, int(number_of_players)) # randomly choose who goes first
            new_game.save() # save new game to db

            # create first player
            new_player = Player()
            new_player.name = form.cleaned_data["creator_name"]
            new_player.game_id = new_game
            new_player.save()

            # create new session to allow the user to play the game
            request.session['player_id'] = new_player.pk

            return render(request, "game_created.html", {
                "form": form,
                "game_code": game_code,
                "n_players": number_of_players,
                "game_id": new_game.pk,
                "your_name": new_player.name,
            })
    else:
        form = GameForm()
        join_form = JoinForm()
        return render(request, "game_creation.html", {"form": form, "join_form": join_form})

def join_game(request):
    logging.warning(request.POST)
    if request.method == "POST":
        form = JoinForm(request.POST)
        if form.is_valid():
            game_id = int(form.cleaned_data['code'])
            input_name = form.cleaned_data['name']
        else:
            return HttpResponseRedirect("/game")

        try:
            game = Game.objects.get(code=game_id)
        except:
            return HttpResponse("Game doesn't exist")

        if(game.joined_players < game.number_of_players):
            # create player and append it to this game
            new_player = Player()
            new_player.name = input_name
            new_player.game_id = game
            new_player.player_number = game.joined_players + 1
            new_player.save()
            # increment the number of players who joined this game
            game.joined_players = game.joined_players + 1
            game.save()

            # create new session to allow the user to play the game
            request.session['player_id'] = new_player.pk
            logging.warning(request.session.items())

            if(new_player.player_number == game.number_of_players): # if this is the last player
                # we now have all the profiles of the players, so we can:
                # generate the deck of cards and shuffle it
                deck = ["1H","1H","1S","1S","1D","1D","1C","1C","2H","2H","2S","2S","2D","2D","2C","2C","3H",
                "3H","3S","3S","3D","3D","3C","3C","4H","4H","4S","4S","4D","4D","4C","4C","5H","5H","5S","5S","5D",
                "5D","5C","5C","6H","6H","6S","6S","6D","6D","6C","6C","7H","7H","7S","7S","7D","7D","7C","7C","8H","8H","8S","8S","8D",
                "8D","8C","8C","9H","9H","9S","9S","9D","9D","9C","9C","10H","10H","10S","10S","10D","10D","10C","10C","11H","11H","11S",
                "11S","11D","11D","11C","11C","12H","12H","12S","12S","12D","12D","12C","12C","13H","13H","13S","13S","13D","13D","13C",
                "13C","14K","14K","14K","14K"]

                # compute how many cards each player will have and the remainder
                cards_per_player = int(108 / game.number_of_players)
                remaining_cards = 108 % game.number_of_players

                random.shuffle(deck) # shuffle the deck
                # give cards_per_player cards to each player
                curr_player_num = 1
                curr_player = Player.objects.get(Q(game_id=game.pk) & Q(player_number=curr_player_num))
                idx = 1

                for card in deck:
                    if((idx % cards_per_player) == 0 and curr_player_num != game.number_of_players): # we filled the last player's hand AND it wasn't the last player: now onto next player
                        curr_player_num = curr_player_num + 1
                        curr_player = Player.objects.get(Q(game_id=game.pk) & Q(player_number=curr_player_num))

                    split_card_str = list(card) # split each character
                    seed = split_card_str[len(split_card_str)-1] # get last character for seed
                    number = int(card[:-1]) # remaining characters are the number
                    
                    # create record in db for curr_player holding this card
                    card_in_hand = CardsInHand()
                    card_in_hand.card_seed = seed
                    card_in_hand.card_number = number
                    card_in_hand.player_id = curr_player
                    card_in_hand.save()

                    idx = idx + 1

            return HttpResponseRedirect("/game/game/" + str(game.pk))
        else:
            return HttpResponse("Full")
    else:
        return HttpResponseRedirect("/game")

def check_session(request):
    try:
        request.session['player_id']
        return HttpResponse(request.session['player_id'])
    except:
        return HttpResponse("who are you?")

def game(request, game_id):
    try: # check if requested game exists
        this_game = Game.objects.get(pk=game_id)
    except:
        return HttpResponse("Specified game doesn't exist")
    
    # get players who joined this game
    players = Player.objects.filter(game_id=game_id)

    if('player_id' not in request.session): # check if user has a session variable player_id
        return HttpResponse("Unauthenticated user")
    
    try: # check if there is a user with id equal to the one in the session variable
        this_player = Player.objects.get(pk=request.session['player_id'])
    except:
        return HttpResponse("Player doesn't exist")

    if(this_player not in players): # check if this player has joined the game
        return HttpResponse("You don't have access to this game")

    try:
        turn_player_name = Player.objects.get(Q(game_id=this_game) & Q(player_number=this_game.player_current_turn)).name
    except:
        turn_player_name = '-'

    # return HttpResponse("Success! You are playing this game")
    return render(request, 'game.html', {
        'n_p' : range(this_game.number_of_players), # used for printing columns for each player in template
        'game_id': this_game.pk,
        'player_name': this_player.name,
        'player_id': this_player.pk,
        'player_num': this_player.player_number,
        'player_num_decremented': this_player.player_number-1, # for comparison in template
        'n_players': this_game.number_of_players,
        'turn': this_game.player_current_turn,
        'turn_player_name': turn_player_name,
        'turn_decremented': this_game.player_current_turn-1,
        'last_turn' : this_game.player_last_turn,
        'col_width': int(100/(this_game.number_of_players-1)), # width of columns to be rendered
        'current_card': this_game.current_card,
        'last_card': this_game.last_card,
    })