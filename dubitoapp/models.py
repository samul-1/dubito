from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import random

from django.db import transaction


class Info(models.Model):
    online_users = models.PositiveIntegerField(default=0)

    @classmethod
    def get_info(cls):
        info, _ = cls.objects.get_or_create(pk=1)
        return info

    @classmethod
    def update_and_get_online_users(cls, delta):
        with transaction.atomic():
            info = cls.get_info()
            info.online_users += delta
            info.save()
            return info.online_users


class Game(models.Model):
    code = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    coutdown_end = models.DateTimeField(default=None, null=True)
    number_of_players = models.IntegerField()  # TODO positive small integer
    joined_players = models.IntegerField(default=1)  # TODO positive small integer
    player_current_turn = models.IntegerField(null=True)  # TODO positive small integer
    player_last_turn = models.IntegerField(
        default=-1
    )  # TODO positive small integer or None
    current_card = models.IntegerField(
        null=True, default=0
    )  # TODO positive small integer

    last_card = models.IntegerField(null=True, default=0)  # TODO unused, remove

    stacked_cards = models.JSONField(default=list, blank=True)
    last_amount_played = models.IntegerField(default=0)  # TODO positive small integer
    locked = models.BooleanField(
        default=False
    )  # used to prevent actions while there are interruptions
    has_begun = models.BooleanField(default=False)
    winning_player = models.IntegerField(  # TODO positive small integer or None
        default=-1
    )  # contains the number of a player that currently has 0 cards
    has_been_won = models.BooleanField(default=False)
    restarted = models.IntegerField(
        default=0
    )  # counts how many time the game has been restarted
    events = models.IntegerField(
        default=0
    )  # counts the number of state-changing events that took place during game
    is_public = models.BooleanField(
        default=False
    )  # True if game was created automatically through matchmaking

    def __str__(self):
        return str(self.code)

    @classmethod
    def try_lock(cls, game_id):
        # atomically check if the game is locked and lock it if it isn't, returns True upon success
        with transaction.atomic():
            game = cls.objects.select_for_update().get(pk=game_id)
            if game.locked:
                return False
            game.locked = True
            game.save(update_fields=["locked"])
            return True

    def get_last_player(self):
        return Player.objects.get(game_id=self.pk, player_number=self.player_last_turn)

    def pass_turn(self):
        return self.increment_turn(
            skip_win_condition_check=True, skip_last_player_update=True
        )

    def increment_turn(self, **kwargs):
        return self.update_turn(
            (self.player_current_turn % self.number_of_players) + 1, **kwargs
        )

    def update_turn(
        self,
        next_player_num,
        skip_win_condition_check=False,
        skip_last_player_update=False,
    ):
        # when a player's turn ends, verify whether there was a player who
        # had no cards left, and if they still have no cards left, they win
        winner = (
            self.verify_or_revoke_victory() if not skip_win_condition_check else None
        )

        update_fields = ["player_current_turn", "player_last_turn"]

        # if the game hasn't been won, check whether the last player has more
        # cards left, and if they don't, set that player as the winning player
        if winner is None:
            last_player_has_more_cards = self.players.get(
                player_number=self.player_current_turn
            ).cards.exists()

            if not last_player_has_more_cards:
                self.winning_player = self.player_current_turn
                update_fields.append("winning_player")

        # update the turn
        self.player_last_turn, self.player_current_turn = (
            self.player_current_turn
            if not skip_last_player_update
            else self.player_last_turn,
            next_player_num,
        )
        self.save(update_fields=update_fields)

        return winner

    def verify_or_revoke_victory(self):
        if self.winning_player == -1:
            return

        winning_player = self.players.get(player_number=self.winning_player)
        if not winning_player.cards.all().exists():
            self.has_been_won = True
            self.save(update_fields=["has_been_won"])
            return self.winning_player

        self.winning_player = -1
        self.save(update_fields=["winning_player"])
        return None

    # TODO make atomic
    def perform_doubt(self, doubter_id):
        stack = self.stacked_cards
        uncovered_cards = self.stacked_cards[(-self.last_amount_played) :]
        doubted_id = self.get_last_player().pk  # this is who was doubted

        successful = False  # failure for who doubted
        # compare cards against claimed card
        claimed_card = self.current_card
        for card in uncovered_cards:
            _, number = CardsInHand.from_card_string(card)
            if number != claimed_card and number != CardsInHand.JOKER_NUMBER:
                successful = True  # success for who doubted
                break

        doubter = Player.objects.get(pk=doubter_id)
        doubted = Player.objects.get(pk=doubted_id)
        if successful:
            winner, loser = doubter, doubted
        else:
            winner, loser = doubted, doubter

        # add whole stack to loser's hand
        for card in self.stacked_cards:
            CardsInHand.create_from_card_string(card, loser.pk)

        # remove any cards for which the loser has all seeds in their hand
        removed_card_ranks, has_more_cards = loser.remove_complete_ranks_from_hand()

        if not has_more_cards:
            self.winning_player = loser.player_number
            self.save(update_fields=["winning_player"])

        self.stacked_cards = []

        self.save(update_fields=["stacked_cards"])

        # it is now the winner's turn
        game_winner = self.update_turn(winner.player_number)

        return {
            "stack": stack,
            "removed_ranks": removed_card_ranks,
            "successful": successful,
            "loser": loser,
        }, game_winner

    # TODO make atomic
    def perform_start_round(self, player_id, rank, cards):
        self.current_card = rank
        self.save(update_fields=["current_card"])

        return self.perform_play_cards(player_id, cards)

    # TODO make atomic
    def perform_play_cards(self, player_id, cards):
        player = Player.objects.get(pk=player_id)

        # remove cards from player's hand and add them to the stack
        player.remove_cards_from_hand(cards)
        self.stacked_cards = [*self.stacked_cards, *cards]

        self.last_amount_played = len(cards)

        self.save(update_fields=["stacked_cards", "last_amount_played"])

        winner = self.increment_turn()
        return winner

    def instantiate(self):  # takes care of the game creation routine
        # generate a random code for the game
        self.code = random.randint(10000, 99999)
        # randomly choose who will go first
        self.player_current_turn = random.randint(1, self.number_of_players)

    def reset(self):  # resets game for replaying
        players = Player.objects.filter(game_id=self)
        CardsInHand.objects.filter(player_id__in=players).delete()

        self.events = 0
        self.restarted += 1
        self.player_current_turn = random.randint(1, self.number_of_players)
        self.winning_player = -1
        self.has_been_won = False
        self.current_card = 0
        self.stacked_cards = "[]"
        self.last_amount_played = 0
        self.locked = False
        self.player_last_turn = -1
        self.joined_players = 0
        self.save()

    # TODO add a parameter to specify the number of decks, whether 1, 1.5 or 2
    def deal_cards_to_players(
        self,
    ):  # called after all players have joined; deals each player their hand of cards
        # generate the deck of cards and shuffle it
        # TODO make this a constant somewhere
        deck = [
            "1H",
            "1H",
            "1S",
            "1S",
            "1D",
            "1D",
            "1C",
            "1C",
            "2H",
            "2H",
            "2S",
            "2S",
            "2D",
            "2D",
            "2C",
            "2C",
            "3H",
            "3H",
            "3S",
            "3S",
            "3D",
            "3D",
            "3C",
            "3C",
            "4H",
            "4H",
            "4S",
            "4S",
            "4D",
            "4D",
            "4C",
            "4C",
            "5H",
            "5H",
            "5S",
            "5S",
            "5D",
            "5D",
            "5C",
            "5C",
            "6H",
            "6H",
            "6S",
            "6S",
            "6D",
            "6D",
            "6C",
            "6C",
            "7H",
            "7H",
            "7S",
            "7S",
            "7D",
            "7D",
            "7C",
            "7C",
            "8H",
            "8H",
            "8S",
            "8S",
            "8D",
            "8D",
            "8C",
            "8C",
            "9H",
            "9H",
            "9S",
            "9S",
            "9D",
            "9D",
            "9C",
            "9C",
            "10H",
            "10H",
            "10S",
            "10S",
            "10D",
            "10D",
            "10C",
            "10C",
            "11H",
            "11H",
            "11S",
            "11S",
            "11D",
            "11D",
            "11C",
            "11C",
            "12H",
            "12H",
            "12S",
            "12S",
            "12D",
            "12D",
            "12C",
            "12C",
            "13H",
            "13H",
            "13S",
            "13S",
            "13D",
            "13D",
            "13C",
            "13C",
            "14K",
            "14K",
            "14K",
            "14K",
        ]

        # compute how many cards each player will have and the remainder
        cards_per_player = int(len(deck) / self.number_of_players)

        random.shuffle(deck)  # shuffle the deck
        # deal cards_per_player cards to each player
        curr_player_num = 1
        curr_player = Player.objects.get(game_id=self.pk, player_number=curr_player_num)
        idx = 1

        for card in deck:
            if (
                idx % cards_per_player
            ) == 0 and curr_player_num != self.number_of_players:
                # we're done dealing to this player and there are more players; onto the next player
                curr_player_num += 1
                curr_player = Player.objects.get(
                    game_id=self.pk, player_number=curr_player_num
                )

            # create record in db for curr_player having this card in their hand
            CardsInHand.create_from_card_string(card, curr_player.pk)

            idx += 1


class Player(models.Model):
    # TODO change to `game`
    game_id = models.ForeignKey(
        Game, on_delete=models.CASCADE, null=True, default=None, related_name="players"
    )
    player_number = models.IntegerField(default=1)
    name = models.CharField(max_length=10)
    is_online = models.BooleanField(default=False)
    has_left = models.BooleanField(
        default=False
    )  # True if player still isn't online when their turn comes
    rejoined = models.BooleanField(
        default=True
    )  # True if player has rejoined the game once it's restarted

    def __str__(self):
        return str(self.pk)

    def add_cards_to_hand(self, cards):
        for card in cards:
            CardsInHand.create_from_card_string(card, self)

    def remove_cards_from_hand(self, cards):
        for card in cards:
            CardsInHand.remove_from_card_string(card, self)

        has_more_cards = self.cards.all().exists()
        return has_more_cards

    def remove_complete_ranks_from_hand(self):
        """
        Removes from the hand of the player any cards for which they have all seeds.
        Returns a list of the removed cards.
        """
        removed_card_ranks = []
        for i in range(1, 14):
            cards_in_hand = self.cards.filter(card_number=str(i))
            if cards_in_hand.count() >= 8:
                # if they have 8 copies of a card, discard those
                cards_in_hand.delete()
                removed_card_ranks.append(str(i))

        has_more_cards = self.cards.all().exists()
        return removed_card_ranks, has_more_cards


class CardsInHand(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="cards")
    card_number = models.IntegerField()
    card_seed = models.CharField(max_length=1)

    JOKER_NUMBER = 14

    @staticmethod
    def from_card_string(
        card_string,
    ):
        split_card_str = list(card_string)  # split each character
        seed = split_card_str[len(split_card_str) - 1]  # get last character for seed
        number = int(card_string[:-1])  # remaining characters are the number
        return (seed, number)

    @classmethod
    def create_from_card_string(
        cls,
        card_string,
        player_id,
    ):
        seed, number = cls.from_card_string(card_string)
        card_in_hand = cls(card_seed=seed, card_number=number, player_id=player_id)
        card_in_hand.save()

    @classmethod
    def remove_from_card_string(
        cls,
        card_string,
        player_id,
    ):
        seed, number = cls.from_card_string(card_string)
        card_in_hand = cls.objects.filter(
            card_seed=seed, card_number=number, player_id=player_id
        )[0]
        card_in_hand.delete()


class Feedback(models.Model):
    sender_name = models.CharField(max_length=50, blank=False)
    email = models.EmailField()
    message = models.TextField(max_length=500)
    timestamp = models.DateTimeField(auto_now=True)
