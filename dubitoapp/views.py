from django.shortcuts import render, redirect
from .models import Game, Player, CardsInHand, Feedback
from django.db.models import Q
from .forms import GameForm, JoinForm, FeedbackForm
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.generic import CreateView
import json

# from django.contrib.auth.decorators import login_required


def get_joined_players(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    return HttpResponse(str(game.joined_players))


def create_new_game(request):
    if request.method == "POST":
        form_data = json.loads(request.body.decode("utf-8"))
        form = GameForm(form_data)

        if form.is_valid():
            number_of_players = form.cleaned_data["number_of_players"]

            new_game = Game(number_of_players=int(number_of_players))
            new_game.instantiate()  # initializes new game
            new_game.save()  # save new game to db

            # create first player
            new_player = Player(
                name=form.cleaned_data["creator_name"], game_id=new_game
            )
            new_player.save()

            # create new session to allow the user to play the game
            request.session["player_id"] = new_player.pk

            return JsonResponse(
                {
                    "code": new_game.code,
                    "game_id": new_game.pk,
                    "number_of_players": number_of_players,
                }
            )
            # return render(request, "game_created.html", {
            #     "form": form,
            #     "game_code": new_game.code,
            #     "n_players": number_of_players,
            #     "game_id": new_game.pk,
            #     "your_name": new_player.name,
            # })
        else:
            return JsonResponse(form.errors.as_json(), safe=False, status=400)
    else:
        # set a dummy player id in player's session. this is needed to make channels session persistence work (for matchmaking)
        if "player_id" not in request.session:
            request.session["player_id"] = 0

        create_form = GameForm(initial={"number_of_players": "2"})
        join_form = JoinForm()
        feedback_form = FeedbackForm()
        return render(
            request,
            "home.html",
            {
                "create_form": create_form,
                "join_form": join_form,
                "feedback_form": feedback_form,
            },
        )


def join_game(request):
    if request.method != "POST":
        return HttpResponseRedirect("/game")

    form_data = json.loads(request.body.decode("utf-8"))
    form = JoinForm(form_data)
    if form.is_valid():
        code = int(form.cleaned_data["code"])
        input_name = form.cleaned_data["name"]
    else:
        return JsonResponse(form.errors.as_json(), safe=False, status=400)

    game = get_object_or_404(Game, code=code)
    if game.joined_players < game.number_of_players:
        # increment the number of players who joined this game
        game.joined_players = game.joined_players + 1
        game.save()
        # create player and append it to this game
        new_player = Player(
            name=input_name, game_id=game, player_number=game.joined_players
        )
        new_player.save()

        # create new session to allow user to play
        request.session["player_id"] = new_player.pk

        if new_player.player_number == game.number_of_players:
            # last player joined: deal cards to all players; game can now being
            game.deal_cards_to_players()

        return JsonResponse(game.pk, safe=False)


def game(request, game_id):
    err_str = ""
    this_game = get_object_or_404(Game, pk=game_id)
    print(request.session.keys())

    # if game is over, redirect to home
    if this_game.has_been_won:
        return redirect(create_new_game)

    # get players who joined this game
    players = Player.objects.filter(game_id=game_id)

    if (
        "player_id" not in request.session
    ):  # check if user has a session variable player_id
        err_str = "Unauthenticated user"

    this_player = get_object_or_404(Player, pk=request.session["player_id"])
    if this_player not in players:  # check if this player has joined the game
        err_str = "La partita richiesta non esiste o si è già conclusa."

    if err_str != "":
        return render(
            request,
            "error.html",
            {
                "error": err_str,
            },
            status=403,
        )

    return render(
        request,
        "game.html",
        {
            "game_id": this_game.pk,
            "number_of_players": this_game.number_of_players,
        },
    )


def feedback_create(request):
    if request.method != "POST":
        return HttpResponseRedirect("/game")

    form_data = json.loads(request.body.decode("utf-8"))
    form = FeedbackForm(form_data)
    if form.is_valid():
        sender_name = form.cleaned_data["sender_name"]
        email = form.cleaned_data["email"]
        message = form.cleaned_data["message"]
    else:
        return JsonResponse(form.errors.as_json(), safe=False, status=400)

    feedback = Feedback(sender_name=sender_name, email=email, message=message)
    feedback.save()
    return JsonResponse("[]", status=200, safe=False)


def restart_game(request, game_id):
    this_game = get_object_or_404(Game, pk=game_id)

    # if game isn't over, redirect to home
    if not this_game.has_been_won:
        return redirect(create_new_game)

    # get players who joined this game
    players = Player.objects.filter(game_id=game_id)

    if (
        "player_id" not in request.session
    ):  # check if user has a session variable player_id
        return redirect(create_new_game)

    this_player = get_object_or_404(Player, pk=request.session["player_id"])
    if this_player not in players:  # check if this player has joined the game
        return redirect(create_new_game)

    this_game.reset()
    this_game.deal_cards_to_players()

    return JsonResponse({"status": "ok"})
