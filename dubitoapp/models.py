from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import random

class Game(models.Model):
    code = models.IntegerField()
    timestamp = models.DateTimeField(auto_now=True)
    number_of_players = models.IntegerField()
    joined_players = models.IntegerField(default=1)
    player_current_turn = models.IntegerField(null=True)
    player_last_turn = models.IntegerField(default=-1)
    current_card = models.IntegerField(null=True, default=0)
    last_card = models.IntegerField(null=True, default=0)
    stacked_cards = models.CharField(max_length=1000, default="[]")
    last_amount_played = models.IntegerField(default=0)
    locked = models.BooleanField(default=False)  # used to prevent actions while there are interruptions
    has_begun = models.BooleanField(default=False)
    winning_player = models.IntegerField(default=-1)  # contains the number of a player that currently has 0 cards
    has_been_won = models.BooleanField(default=False)

    def __str__(self):
        return str(self.code)

    def instantiate(self):  # takes care of the game creation routine
        # generate a random code for the game
        self.code = random.randint(10000, 99999)
        # randomly choose who will go first
        self.player_current_turn = random.randint(1, self.number_of_players)

    def deal_cards_to_players(self):  # called after all players have joined; deals each player their hand of cards
        # generate the deck of cards and shuffle it
        deck = [
            "1H","1H","1S","1S","1D","1D","1C","1C","2H","2H","2S","2S","2D","2D","2C","2C","3H",
            "3H","3S","3S","3D","3D","3C","3C","4H","4H","4S","4S","4D","4D","4C","4C","5H","5H","5S","5S","5D",
            "5D","5C","5C","6H","6H","6S","6S","6D","6D","6C","6C","7H","7H","7S","7S","7D","7D","7C","7C","8H","8H","8S","8S","8D",
            "8D","8C","8C","9H","9H","9S","9S","9D","9D","9C","9C","10H","10H","10S","10S","10D","10D","10C","10C","11H","11H","11S",
            "11S","11D","11D","11C","11C","12H","12H","12S","12S","12D","12D","12C","12C","13H","13H","13S","13S","13D","13D","13C",
            "13C","14K","14K","14K","14K"
        ]

        # compute how many cards each player will have and the remainder
        cards_per_player = int(108 / self.number_of_players)
        remaining_cards = 108 % self.number_of_players

        random.shuffle(deck) # shuffle the deck
        # deal cards_per_player cards to each player
        curr_player_num = 1
        curr_player = Player.objects.get(game_id=self.pk, player_number=curr_player_num)
        idx = 1

        for card in deck:
            if((idx % cards_per_player) == 0 and curr_player_num != self.number_of_players):
                # we're done dealing to this player and there are more players; onto the next player
                curr_player_num += 1
                curr_player = Player.objects.get(game_id=self.pk, player_number=curr_player_num)

            split_card_str = list(card)  # split each character
            seed = split_card_str[len(split_card_str)-1]  # get last character for seed
            number = int(card[:-1])  # remaining characters are the card number
            
            # create record in db for curr_player having this card in their hand
            card_in_hand = CardsInHand(card_seed=seed, card_number=number, player_id=curr_player)
            card_in_hand.save()

            idx = idx + 1

class Player(models.Model):
    game_id = models.ForeignKey(Game, on_delete=models.CASCADE)
    player_number = models.IntegerField(default=1)
    name = models.CharField(max_length=10)
    is_online = models.BooleanField(default=False)
    has_left = models.BooleanField(default=False) # True if the user still isn't online when their turn comes

    def __str__(self):
        return str(self.pk)

class CardsInHand(models.Model):
    player_id = models.ForeignKey(Player, on_delete=models.CASCADE)
    card_number = models.IntegerField()
    card_seed = models.CharField(max_length=1)

class Feedback(models.Model):
    sender_name = models.CharField(max_length=50, blank=False)
    email = models.EmailField()
    message = models.TextField(max_length=500)
    timestamp = models.DateTimeField(auto_now=True)
