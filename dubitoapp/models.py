from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Game(models.Model):
    code = models.IntegerField()
    number_of_players = models.IntegerField()
    joined_players = models.IntegerField(default=1)
    player_current_turn = models.IntegerField(null=True)
    player_last_turn = models.IntegerField(default=-1)
    current_card = models.IntegerField(null=True, default=0)
    last_card = models.IntegerField(null=True, default=0)
    stacked_cards = models.CharField(max_length=1000, default="[]")
    last_amount_played = models.IntegerField(default=0)
    locked = models.BooleanField(default=False) # used to prevent actions while there are interruptions
    has_begun = models.BooleanField(default=False)
    winning_player = models.IntegerField(default=-1)
    has_been_won = models.BooleanField(default=False)

    def __str__(self):
        return str(self.code)

class Player(models.Model):
    game_id = models.ForeignKey(Game, on_delete=models.CASCADE)
    player_number = models.IntegerField(default=1)
    name = models.CharField(max_length=50)
    is_online = models.BooleanField(default=False)
    has_left = models.BooleanField(default=False) # True if the user still isn't online when their turn comes

    def __str__(self):
        return str(self.pk)

class CardsInHand(models.Model):
    player_id = models.ForeignKey(Player, on_delete=models.CASCADE)
    card_number = models.IntegerField()
    card_seed = models.CharField(max_length=1)