import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
import logging
from channels.db import database_sync_to_async
import asyncio
from .models import Game, Player, CardsInHand, Info
from django.db.models import Q
from asgiref.sync import sync_to_async


class GameConsumer(AsyncWebsocketConsumer):
    def get_lock_game_manager(self):
        game_id = self.game_id
        lock_game = self.lock_game
        unlock_game = self.unlock_game

        class AsyncLockGameManager:
            async def __aenter__(self):
                await lock_game(game_id)

            async def __aexit__(self, exc_type, exc, tb):
                if exc_type is not None:
                    logging.error(
                        f"Exception in lock_game context manager for game {str(game_id)}",
                        exc_info=(exc_type, exc, tb),
                    )

                await unlock_game(game_id)

        return AsyncLockGameManager()

    async def send_new_state_to_all_players(self, event_specifics):
        # sends all online players an updated copy of the game state
        # the event_specifics dict contains relevant information about the last event in the game
        await self.increment_event_count(self.game_id)
        for player in await sync_to_async(list)(
            Player.objects.filter(game_id=self.game_id)
        ):
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    "type": "game_state_handler",
                    "player_id": player.pk,
                    "event_specifics": event_specifics,
                },
            )

    async def connect(self):
        # TODO in all methods that explicitly take game_id, use self.game_id instead
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.player_id = self.scope["session"]["player_id"]
        self.game_group_name = "game_%s" % self.game_id

        # Join room group
        await self.channel_layer.group_add(self.game_group_name, self.channel_name)

        # mark player as online
        await self.set_online_status(self.player_id, True)

        # if player is rejoining a restarted game, record that as well
        if not await self.has_rejoined(self.player_id):
            await self.set_rejoined(self.player_id, True)
            await self.increment_joined_players(self.game_id)

        # send new game state to all players
        await self.send_new_state_to_all_players({"type": "player_joined"})

        await self.accept()

    async def disconnect(self, close_code):
        game = await self.get_game()
        await self.channel_layer.group_discard(self.game_group_name, self.channel_name)

        # mark player as offline
        await self.set_online_status(self.player_id, False)

        await self.send_new_state_to_all_players(
            {
                "type": "player_disconnected",
            }
        )

        # player left during their turn
        if await self.get_player_number(self.player_id) == await self.get_current_turn(
            self.game_id
        ):
            await asyncio.sleep(5)  # give the player a chance to come back

            # player hasn't come back after 5 seconds
            if not await self.is_online(self.player_id):
                await sync_to_async(game.pass_turn)()

                await self.send_new_state_to_all_players(
                    {
                        "type": "pass_turn",
                    }
                )
                await self.check_current_player_online()  # verify that next player is online

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json["type"]

        logging.info(self.scope["session"]["player_id"])
        logging.info(text_data_json)

        if action == "start_round":
            # called when the first player places down card(s) and initiates a round
            claimed_card = text_data_json["claimed"]
            cards = text_data_json["cards"]
            await self.start_round(claimed_card, cards)
        elif action == "doubt":
            # called when a player interrupts game to doubt
            await self.doubt()
        elif action == "place_cards":
            # called when a player places down card(s)
            cards = text_data_json["cards"]
            await self.place_cards(cards)
        elif action == "reaction":
            # called when a player clicks on a reaction button
            reaction = text_data_json["reaction"]
            await self.send_reaction(reaction)
        elif action == "chat_message":
            message = text_data_json["message"]
            await self.send_message(message)
        elif action == "restart":
            await self.restart_game()

        logging.info("event processed correctly")

    async def start_round(self, claimed_card, cards):
        # TODO all these checks should be done inside the lock, especially the lock check
        game = await self.get_game()
        # Sends claimed card information and saves placed cards to db
        if await self.check_card_possession(self.game_id, self.player_id, cards):
            # player is illegally trying to play cards they don't have
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to place cards they don't have: "
                + str(cards)
            )
            return

        # TODO use try_lock from Game instead of separately checking and locking
        if await self.is_locked(self.game_id):
            # someone else got here first
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to start round while game is locked"
            )
            return

        if await self.get_current_turn(self.game_id) != await self.get_player_number(
            self.player_id
        ):
            # wrong player trying to play
            logging.warning(
                await self.get_player_name(self.player_id)
                + " trying to start round but it's wrong turn"
            )
            return

        if not len(cards):
            # trying to place 0 cards
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to place 0 cards"
            )
            return

        # You can't start two consecutive rounds with the same card
        if int(claimed_card) == await self.get_current_card(self.game_id):
            logging.info(
                await self.get_player_name(self.player_id)
                + " is trying to place same rank two consecutive turns"
            )
            return

        async with self.get_lock_game_manager():
            # update current card, place selected cards onto the stack, and remove them from player's hand
            game_winner = await sync_to_async(game.perform_start_round)(
                self.player_id,
                claimed_card,
                cards,
            )

            if game_winner is not None:
                await self.send_game_has_been_won()

            # contains information specific to this type of event that will be used by the client
            # to play the corresponding animations
            event_specifics = {
                "type": "cards_placed",
                "by_who": await self.get_player_number(self.player_id),
                "number_of_cards_placed": len(cards),
            }

            await self.send_new_state_to_all_players(event_specifics)

        await self.check_current_player_online()  # handle the case where current player isn't online

    async def doubt(self):
        # TODO all these checks should be done inside the lock, especially the lock check
        if await self.is_locked(self.game_id):
            # someone else got here first
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to doubt while game is locked"
            )
            return

        game = await self.get_game()
        last_player_id = await self.get_player_last_turn(self.game_id)
        if (
            game.last_amount_played == 0
            or not game.stacked_cards
            or last_player_id is None
        ):
            # trying to doubt before any card has been placed
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to doubt before any cards placed"
            )
            return

        if self.player_id == last_player_id:
            # player doubted themselves
            logging.warning(
                await self.get_player_name(self.player_id) + " doubted themselves"
            )
            return

        async with self.get_lock_game_manager():
            outcome, game_winner = await sync_to_async(game.perform_doubt)(
                self.player_id
            )

            if game_winner is not None:
                await self.send_game_has_been_won()

            event_specifics = {
                "type": "doubt",
                "who_doubted": await self.get_player_name(self.player_id),
                # TODO this is redundant, remove when you fix frontend
                "who_doubted_number": await self.get_player_number(self.player_id),
                "who_was_doubted": await self.get_player_name(game.player_last_turn),
                # TODO rename to successful in frontend
                "outcome": outcome["successful"],
                # TODO rename to just stack in frontend
                "whole_stack": outcome["stack"],
                "copies_removed": outcome["removed_ranks"],
                "losing_player": outcome["loser"].name,
            }

            await self.send_new_state_to_all_players(event_specifics)

        await self.check_current_player_online()  # handle the case where current player isn't online

    async def place_cards(self, cards):
        # TODO all these checks should be done inside the lock, especially the lock check
        game = await self.get_game()
        # Sends amount of cards of current number placed and saves placed cards to db
        if await self.check_card_possession(self.game_id, self.player_id, cards):
            # player is illegally trying to play cards they don't have
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to place cards they don't have: "
                + str(cards)
            )
            return

        if await self.is_locked(self.game_id):
            # someone else got here first
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to place cards while game is locked"
            )
            return

        player_number = await self.get_player_number(self.player_id)

        # TODO replace player number with player id
        if await self.get_current_turn(self.game_id) != player_number:
            # wrong player trying to play
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to place cards but it's wrong turn"
            )
            return

        if not len(cards):
            # trying to place 0 cards
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to place 0 cards"
            )
            return

        async with self.get_lock_game_manager():
            # place selected cards onto the stack and remove them from user's hand
            game_winner = await sync_to_async(game.perform_play_cards)(
                self.player_id,
                cards,
            )

            if game_winner is not None:
                await self.send_game_has_been_won()

            # contains information specific to this type of event that will be used by the client
            # to play the corresponding animations
            event_specifics = {
                "type": "cards_placed",
                "by_who": player_number,
                "number_of_cards_placed": len(cards),
            }

            await self.send_new_state_to_all_players(event_specifics)

        await self.check_current_player_online()  # handle the case where current player isn't online

    async def check_current_player_online(self):
        game = await self.get_game()
        # verifies the current turn player is online, and if they aren't, passes turn onto next player
        current_turn_player_number = await self.get_current_turn(self.game_id)
        while (
            not await self.is_online(
                await self.get_player_id_from_number(
                    self.game_id, current_turn_player_number
                )
            )
            and await self.number_of_online_players(self.game_id) > 0
        ):
            # if player isn't online, increment turn, and iterate until you find a player that is online
            await sync_to_async(game.pass_turn)()

            current_turn_player_number = await self.get_current_turn(self.game_id)

            await self.send_new_state_to_all_players(
                {
                    "type": "pass_turn",
                }
            )

    async def send_reaction(self, reaction):
        # Called when a player clicks on a reaction button
        if reaction not in [
            "laughing",
            "crying",
            "drunk",
            "smirk",
            "thinking",
            "angry",
        ]:
            # only allow supported emojis
            return

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                "type": "reaction_handler",
                "who": self.player_id,
                "reaction": reaction,
            },
        )

    async def send_message(self, message):
        # Called when a player sends a chat message
        if len(message) > 70:
            return

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                "type": "message_handler",
                "who": self.player_id,
                "message": message,
            },
        )

    async def restart_game(self):
        # Called when a player wants to play again at the end of a game
        if not await self.game_has_been_won(self.game_id):
            logging.warning(
                await self.get_player_name(self.player_id)
                + " is trying to restart game before it's ended"
            )
            return

        await self.restart_game_routine(self.game_id)

        for player in await sync_to_async(list)(await self.get_players(self.game_id)):
            await self.set_online_status(player.pk, False)
            await self.set_rejoined(player.pk, False)  # TODO is this necessary?

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                "type": "restarted_handler",
                "restarted_by": await self.get_player_number(self.player_id),
            },
        )

    async def send_game_has_been_won(self):
        game = await self.get_game()
        winning_player = game.winning_player
        winning_player_id = await self.get_player_id_from_number(
            self.game_id, winning_player
        )

        event_specifics = {
            "type": "player_won",
            "winner": await self.get_player_name(winning_player_id),
        }
        await self.send_new_state_to_all_players(event_specifics)
        # TODO eventually this won't be necessary
        await self.lock_game(self.game_id)

    # HANDLERS
    async def game_state_handler(self, event):
        if self.player_id != event["player_id"]:
            return
        state = await self.get_game_state(self.game_id, event["player_id"])
        await self.send(
            text_data=json.dumps(
                {
                    "type": "new_state",
                    "state": state,
                    "event_specifics": event["event_specifics"],
                }
            )
        )

    async def reaction_handler(self, event):
        if self.player_id == event["who"]:
            # don't send reaction back to the player who sent the event
            return

        await self.send(
            text_data=json.dumps(
                {
                    "event_specifics": {
                        "type": "reaction",
                        "reaction": event["reaction"],
                        "who": await self.get_player_number(event["who"]),
                    },
                }
            )
        )

    async def message_handler(self, event):
        if self.player_id == event["who"]:
            # don't send reaction back to the player who sent the event
            return

        await self.send(
            text_data=json.dumps(
                {
                    "event_specifics": {
                        "type": "message",
                        "message": event["message"],
                        "who": await self.get_player_number(event["who"]),
                    },
                }
            )
        )

    async def restarted_handler(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "event_specifics": {
                        "type": "restart",
                        "by": event["restarted_by"],
                    },
                }
            )
        )

    # UTILS

    @database_sync_to_async
    def number_of_online_players(self, game_id):
        game = Game.objects.get(pk=game_id)
        return Player.objects.filter(game_id=game, is_online=True).count()

    @database_sync_to_async
    def increment_turn(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.player_last_turn = game.player_current_turn
        game.player_current_turn = (
            game.player_current_turn % game.number_of_players
        ) + 1
        game.save(update_fields=["player_last_turn", "player_current_turn"])

    @database_sync_to_async
    def get_hand(self, player_id):
        cards = CardsInHand.objects.filter(player_id=player_id)
        return list(cards.values("card_seed", "card_number"))

    @database_sync_to_async
    def is_locked(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.locked

    @database_sync_to_async
    def lock_game(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.locked = True
        game.save(update_fields=["locked"])

    @database_sync_to_async
    def unlock_game(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.locked = False
        game.save(update_fields=["locked"])

    @database_sync_to_async
    def get_game(self):
        return Game.objects.get(pk=self.game_id)

    @database_sync_to_async
    def get_current_turn(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.player_current_turn

    @database_sync_to_async
    def get_player_last_turn(
        self, game_id
    ):  # returns id of last player who put down cards
        game = Game.objects.get(pk=game_id)
        num = game.player_last_turn

        try:
            player = Player.objects.get(game_id=game_id, player_number=num)
            return player.pk
        except Player.DoesNotExist:
            return None

    @database_sync_to_async
    def get_stacked_cards(
        self, game_id, amount=0
    ):  # get a list of the cards that are on the stack
        game = Game.objects.get(pk=game_id)
        selected_cards = game.stacked_cards[-amount:]
        if selected_cards == []:
            return None
        return selected_cards

    @database_sync_to_async
    def set_stacked_cards(self, game_id, cards):
        game = Game.objects.get(pk=game_id)
        game.stacked_cards = cards
        game.last_amount_played = len(cards)
        game.save(update_fields=["stacked_cards", "last_amount_played"])

    @database_sync_to_async
    def get_last_amount_played(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.last_amount_played

    @database_sync_to_async
    def get_current_card(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.current_card

    @database_sync_to_async
    def set_current_card(self, game_id, card_number):
        game = Game.objects.get(pk=game_id)
        game.current_card = card_number
        game.save(update_fields=["current_card"])

    @database_sync_to_async
    def check_card_possession(self, game_id, player_id, cards):
        # returns 0 if the requested player has all the requested cards in their hand, 1 otherwise
        cards_counted = {}
        for card in cards:
            if card not in cards_counted:
                cards_counted[card] = 1
            else:
                cards_counted[card] = cards_counted[card] + 1

        for card in cards:
            # for every card, see if the number of times it appear is greater than
            # the number of copies of it the player has in their hand
            seed, number = CardsInHand.from_card_string(card)
            if (
                CardsInHand.objects.filter(
                    player_id=player_id, card_seed=seed, card_number=int(number)
                ).count()
                < cards_counted[card]
            ):
                return True
        return False

    @database_sync_to_async
    def get_player_number(self, player_id):
        player = Player.objects.get(pk=player_id)
        return player.player_number

    @database_sync_to_async
    def get_player_id_from_number(self, game_id, player_num):
        try:
            return Player.objects.get(
                Q(game_id=game_id) & Q(player_number=player_num)
            ).pk
        except Player.DoesNotExist:
            return None

    @database_sync_to_async
    def get_number_of_cards_in_hand(self, player_id):
        return CardsInHand.objects.filter(player_id=player_id).count()

    @database_sync_to_async
    def get_player_name(self, player_id):
        player = Player.objects.get(pk=player_id)
        return player.name

    @database_sync_to_async
    def get_players(self, game_id):
        return Player.objects.filter(game_id=game_id)

    @database_sync_to_async
    def get_amount_of_card_in_hand(self, player_id, card_number):
        return len(
            CardsInHand.objects.filter(player_id=player_id, card_number=card_number)
        )

    @database_sync_to_async
    def set_winning_player(self, game_id, player_number):
        game = Game.objects.get(pk=game_id)
        game.winning_player = player_number
        game.save()

    @database_sync_to_async
    def get_game_state(self, game_id, player_id):
        # Returns a dictionary containing the game state
        game = Game.objects.get(pk=game_id)

        this_player = Player.objects.get(pk=player_id)
        this_player_cards = CardsInHand.objects.filter(player_id=player_id)
        my_cards = []
        for card in this_player_cards:
            card_str = str(card.card_number) + card.card_seed
            my_cards.append(card_str)

        other_players_list = []
        other_players = Player.objects.filter(Q(game_id=game_id) & ~Q(pk=player_id))
        for player in other_players:
            player_data = {
                "number": player.player_number,
                "is_online": player.is_online,
                "number_of_cards": CardsInHand.objects.filter(player_id=player).count(),
                "name": player.name,
            }
            other_players_list.append(player_data)

        all_players_joined = game.number_of_players == game.joined_players

        state = {
            "last_turn": game.player_last_turn,
            "current_card": game.current_card,
            "last_card": game.last_card,
            "last_amount_played": game.last_amount_played,
            "won_by": game.winning_player if game.has_been_won else -1,
            "my_cards": my_cards,
            "other_players_data": other_players_list,
            "my_player_number": this_player.player_number,
        }

        if all_players_joined:
            state["current_turn"] = game.player_current_turn
            state["number_of_stacked_cards"] = len(game.stacked_cards)
            state["all_players_joined"] = 1
        else:
            state["all_players_joined"] = 0
            state["number_of_stacked_cards"] = 0.1

        return state

    @database_sync_to_async
    def is_online(self, player_id):
        player = Player.objects.get(pk=player_id)
        return player.is_online

    @database_sync_to_async
    def has_left(self, player_id):
        player = Player.objects.get(pk=player_id)
        return player.has_left

    @database_sync_to_async
    def set_online_status(self, player_id, value=True):
        try:
            player = Player.objects.get(pk=player_id)
        except:
            return
        player.is_online = value
        if value and player.has_left:
            player.has_left = False
        player.save()

    @database_sync_to_async
    def set_has_left(self, player_id):
        player = Player.objects.get(pk=player_id)

        player.has_left = True
        player.save(update_fields=["has_left"])

    @database_sync_to_async
    def set_game_has_been_won(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.has_been_won = True
        game.save(update_fields=["has_been_won"])

    @database_sync_to_async
    def game_has_been_won(self, game_id):
        return Game.objects.get(pk=game_id).has_been_won

    @database_sync_to_async
    def restart_game_routine(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.reset()
        game.deal_cards_to_players()

    @database_sync_to_async
    def has_rejoined(self, player_id):
        return Player.objects.get(pk=player_id).rejoined

    @database_sync_to_async
    def set_rejoined(self, player_id, to):
        player = Player.objects.get(pk=player_id)
        player.rejoined = to
        player.save(update_fields=["rejoined"])

    @database_sync_to_async
    def all_players_joined(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.number_of_players == game.joined_players

    @database_sync_to_async
    def increment_joined_players(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.joined_players += 1
        game.save(update_fields=["joined_players"])

    @database_sync_to_async
    def increment_event_count(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.events += 1
        game.save(update_fields=["events"])


class MatchmakingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group = "matchmaking_pool"

        # Join room group
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        online_players_count = await self.update_online_user_count_and_get_value(
            increment=1
        )

        if online_players_count > 1:
            await self.channel_layer.group_send(
                self.group,
                {
                    "type": "online_players_handler",
                    "value": 1,
                },
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json["type"]

        if action == "join_matchmaking":
            player_name = text_data_json["player_name"]
            await self.join_matchmaking(player_name)

    async def join_matchmaking(self, player_name):
        if len(player_name) > 10:
            logging.warning(player_name + " is too long!")
            return

        self.player_name = player_name
        logging.info(self.player_name + " has started matchmaking")

        # save new player id to session
        player = await self.create_new_player(self.player_name)
        self.scope["session"]["player_id"] = player.pk
        await database_sync_to_async(
            self.scope["session"].save
        )()  # TODO what does this do?

        # look for an available game
        available_game = await self.get_available_game(less_than_joined_players=6)

        # join user to available game and send user its id
        if available_game is not None:
            await self.join_user_to_game(player, available_game)
            # inform every player associated to this game that a new player joined
            await self.channel_layer.group_send(
                self.group,
                {
                    "type": "player_found_handler",
                    "game_id": available_game.pk,
                },
            )
            if available_game.joined_players == 2:
                # as soon as the second player joins, schedule dealing of cards
                loop = asyncio.get_event_loop()
                loop.create_task(self.deal_cards_task(available_game.pk))
        # create a new game
        else:
            new_game = await self.create_public_game()
            await self.join_user_to_game(player, new_game)

    async def disconnect(self, close_code):
        online_players_count = await self.update_online_user_count_and_get_value(
            increment=-1
        )

        if online_players_count < 2:
            await self.channel_layer.group_send(
                self.group,
                {
                    "type": "online_players_handler",
                    "value": 0,
                },
            )

        # if player hadn't joined matchmaking, just discard them from group (no further action required)
        if "player_id" not in self.scope["session"]:
            await self.channel_layer.group_discard(self.group, self.channel_name)
            return

        session_player_id = self.scope["session"]["player_id"]

        game = await self.get_joined_game_from_player_id(session_player_id)

        if game is None or await self.has_begun(game):
            await self.channel_layer.group_discard(self.group, self.channel_name)
            return

        logging.info(str(session_player_id) + " has left matchmaking")

        # delete player and decrement number of joined players to game
        await self.decrement_joined_players(game)
        await self.delete_player_from_id(session_player_id)
        print("deleting " + str(session_player_id))

        if await self.get_joined_players_number(game) == 1:
            # if the player who left was the last aside from the one that created the game,
            # tell that player to reset the timer because there are no players anymore
            await self.channel_layer.group_send(
                self.group,
                {
                    "type": "reset_timer_handler",
                    "game_id": game.pk,
                },
            )

        # if player was the only one online, delete the game that was created due to them connecting
        await self.delete_game_if_no_players(game)
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def player_found_handler(self, event):
        if self.scope["session"]["player_id"] not in await sync_to_async(list)(
            await self.get_joined_player_ids(event["game_id"])
        ):
            # only send information to players joined to this game
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "player_found",
                    "game_id": event["game_id"],
                }
            )
        )

    async def reset_timer_handler(self, event):
        if self.scope["session"]["player_id"] not in await sync_to_async(list)(
            await self.get_joined_player_ids(event["game_id"])
        ):
            # only send information to players joined to this game
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "reset_timer",
                }
            )
        )

    async def online_players_handler(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "online_players",
                    "value": event["value"],
                }
            )
        )

    async def deal_cards_task(self, game_id):
        await asyncio.sleep(9)
        await self.call_deal_cards(game_id)
        await self.begin_game(game_id)

    @database_sync_to_async
    def create_new_player(self, name):
        new_player = Player(name=name)
        new_player.save()
        return new_player

    @database_sync_to_async
    def get_available_game(self, less_than_joined_players):
        # TODO prioritize games with less joined players
        from random import choice

        qs = Game.objects.filter(
            is_public=True,
            joined_players__lt=less_than_joined_players,
        )
        if qs.count() == 0:
            return None
        return choice(qs)

    @database_sync_to_async
    def join_user_to_game(self, player, game):
        # TODO use a count query instead of joined_players
        game.joined_players += 1
        game.number_of_players += 1
        game.save()

        player.player_number = game.joined_players
        player.game_id = game
        player.save()

    @database_sync_to_async
    def create_public_game(self):
        new_game = Game(is_public=True, code=0, number_of_players=0, joined_players=0)
        new_game.save()
        return new_game

    @database_sync_to_async
    def get_joined_player_ids(self, game_id):
        game = Game.objects.get(pk=game_id)
        return map(lambda p: p.pk, Player.objects.filter(game_id=game))

    @database_sync_to_async
    def get_joined_players_number(self, game):
        return game.joined_players

    @database_sync_to_async
    def call_deal_cards(self, game_id):
        import random

        game = Game.objects.get(pk=game_id)
        if game.joined_players == 1 or game.has_begun:
            return
        game.deal_cards_to_players()
        game.is_public = False
        game.player_current_turn = random.randint(1, game.number_of_players)
        game.save()

    @database_sync_to_async
    def get_joined_game_from_player_id(self, player_id):
        try:
            return Player.objects.get(pk=player_id).game_id
        except:
            return None

    @database_sync_to_async
    def delete_game_if_no_players(self, game):
        if game.joined_players == 0:
            game.delete()

    @database_sync_to_async
    def decrement_joined_players(self, game):
        game.joined_players -= 1
        game.number_of_players -= 1
        game.save()

    @database_sync_to_async
    def delete_player_from_id(self, player_id):
        player = Player.objects.get(pk=player_id)
        player.delete()

    @database_sync_to_async
    def has_begun(self, game):
        return game.has_begun

    @database_sync_to_async
    def begin_game(self, game_id):
        game = Game.objects.get(pk=game_id)
        if game.joined_players == 1:
            return
        game.has_begun = True
        game.save()

    @database_sync_to_async
    def update_online_user_count_and_get_value(self, increment):
        online_users = Info.update_and_get_online_users(increment)
        return online_users
