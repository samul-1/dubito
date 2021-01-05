import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
import logging
from channels.db import database_sync_to_async
import asyncio
from .models import Game, Player, CardsInHand
from django.db.models import Q
from asgiref.sync import sync_to_async


class GameConsumer(AsyncWebsocketConsumer):
    async def send_new_state_to_all_players(self, event_specifics):
        # sends all online players an updated copy of the game state
        # the event_specifics dict contains relevant information about the last event in the game
        for player in await sync_to_async(list)(Player.objects.filter(Q(game_id=self.game_id))):
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'game_state_handler',
                    'player_id': player.pk,
                    'event_specifics': event_specifics,
                }
            )

    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.player_id = self.scope['session']['player_id']
        self.game_group_name = 'game_%s' % self.game_id

        # Join room group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        # mark player as online
        await self.set_online_status(self.player_id, True)

        # send new game state to all players
        await self.send_new_state_to_all_players({
            'type': 'player_joined'
        })

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )

        # mark player as offline
        await self.set_online_status(self.player_id, False)

        await self.send_new_state_to_all_players({
            'type': 'player_disconnected',
        })

        if await self.get_player_number(self.player_id) == await self.get_current_turn(self.game_id): 
            # player left during their turn
            await asyncio.sleep(5)  # give the player a chance to come back
            if not await self.is_online(self.player_id):  # player hasn't come back ater 5 seconds
                await self.pass_turn(self.game_id)  # pass turn onto next player
                await self.send_new_state_to_all_players({
                    'type': 'pass_turn',
                })
                await self.check_current_player_online()  # verify that next player is online

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json['type']

        if action == 'start_round':
            # called when the first player places down card(s) and initiates a round
            claimed_card = text_data_json['claimed']
            cards = text_data_json['cards']
            await self.start_round(claimed_card, cards)
        elif action == 'doubt':
            # called when a player interrupts game to doubt
            await self.doubt()
        elif action == 'place_cards':
            # called when a player places down card(s)
            cards = text_data_json['cards']
            await self.place_cards(cards)
        elif action == 'reaction':
            # called when a player clicks on a reaction button
            reaction = text_data_json['reaction']
            await self.send_reaction(reaction)

    async def start_round(self, claimed_card, cards):
        # Sends claimed card information and saves placed cards to db

        if(await self.check_card_possession(self.game_id, self.player_id, cards)):
            # player is illegally trying to play cards they don't have
            return

        if await self.is_locked(self.game_id):
            # someone else got here first
            return

        if await self.get_current_turn(self.game_id) != await self.get_player_number(self.player_id):
            # wrong player trying to play
            return

        if not len(cards):
            # trying to place 0 cards
            return

        # You can't start two consecutive rounds with the same card
        if int(claimed_card) == await self.get_current_card(self.game_id):
            return

        await self.lock_game(self.game_id)  # prevent further action from other players

        # update current card, place selected cards onto the stack, and remove them from player's hand
        await self.set_current_card(self.game_id, claimed_card)
        await self.set_stacked_cards(self.game_id, cards)
        await self.remove_from_hand(self.game_id, self.player_id, cards)

        # if a player had zero cards and was eligible to win, verify they still have zero cards after this action
        await self.verify_or_revoke_victory(self.game_id)

        if not await self.get_number_of_cards_in_hand(self.player_id):
            # player has no more cards; set them as eligible to win
            await self.set_winning_player(self.game_id, await self.get_player_number(self.player_id))

        # contains information specific to this type of event that will be used by the client
        # to play the corresponding animations
        event_specifics = {
            'type': 'cards_placed',
            'by_who': await self.get_player_number(self.player_id),
            'number_of_cards_placed': len(cards),
        }

        await self.increment_turn(self.game_id)
        await self.send_new_state_to_all_players(event_specifics)
        await self.unlock_game(self.game_id)  # resume normal game flow
        await self.check_current_player_online()  # handle the case where current player isn't online
    
    async def check_current_player_online(self):
        # verifies the current turn player is onine, and if they aren't, passes turn onto next player
        current_turn_player_number = await self.get_current_turn(self.game_id)
        while not await self.is_online(await self.get_player_id_from_number(self.game_id, current_turn_player_number)):
            # if player isn't online, increment turn, and iterate until you find a player that is online
            await self.pass_turn(self.game_id)
            current_turn_player_number = await self.get_current_turn(self.game_id)

            await self.send_new_state_to_all_players({
                'type': 'pass_turn',
            })

    async def doubt(self):
        if await self.is_locked(self.game_id):
            # someone else got here first
            return

        if await self.get_player_last_turn(self.game_id) is None or await self.get_last_amount_played(self.game_id) == 0 or await self.get_stacked_cards(self.game_id) is None:
            # trying to doubt before any card has been placed
            return

        if self.player_id == await self.get_player_last_turn(self.game_id):
            # player doubted themselves
            return

        await self.lock_game(self.game_id)  # prevent further action from other players

        # get last cards played from the stack
        uncovered_cards = await self.get_stacked_cards(
            self.game_id,
            await self.get_last_amount_played(self.game_id)
        )
        outcome = 0  # 0 if who was doubted wins, 1 if doubter wins
        copies_removed = []

        # compare cards against claimed card
        for card in uncovered_cards:
            split_card_str = list(card)  # split each character
            number = int(card[:-1])  # remaining characters are the number
            claimed_card = await self.get_current_card(self.game_id)
            if(number != claimed_card and number != 14):  # 14 is the wildcard
                outcome = 1  # success for who doubted
                break

        whole_stack = await self.get_stacked_cards(self.game_id)
        who_doubted = self.player_id
        last_player = await self.get_player_last_turn(self.game_id) # this is who was doubted

        if(outcome):
            winner = who_doubted
            loser = last_player
            # await self.add_to_hand(self.game_id, last_player, whole_stack)
            # for i in range(1, 14):
            #     if await self.get_amount_of_card_in_hand(last_player, str(i)) == 8: # if they have 8 copies of a card, discard those
            #         await self.remove_all_cards(last_player, str(i))
            #         copies_removed.append(str(i))
            #         if not await self.get_number_of_cards_in_hand(last_player): # player has no more cards
            #             await self.set_winning_player(self.game_id, await self.get_player_number(last_player))
            # await self.set_new_turn(self.game_id, await self.get_player_number(who_doubted))

        else:
            winner = last_player
            loser = who_doubted
            # await self.add_to_hand(self.game_id, who_doubted, whole_stack)
            # for i in range(1, 14):
            #     if await self.get_amount_of_card_in_hand(who_doubted, str(i)) == 8: # if they have 8 copies of a card, discard those
            #         await self.remove_all_cards(who_doubted, str(i))
            #         copies_removed.append(str(i))
            #         if not await self.get_number_of_cards_in_hand(who_doubted): # player has no more cards
            #             await self.set_winning_player(self.game_id, await self.get_player_number(who_doubted))
            # await self.set_new_turn(self.game_id, await self.get_player_number(last_player))

        # add the whole stack to loser player's hand
        await self.add_to_hand(self.game_id, loser, whole_stack)
        for i in range(1, 14):
            if await self.get_amount_of_card_in_hand(loser, str(i)) == 8:
                # if they have 8 copies of a card, discard those
                await self.remove_all_cards(loser, str(i))
                copies_removed.append(str(i))
                if not await self.get_number_of_cards_in_hand(loser):  # player has no more cards
                    await self.set_winning_player(self.game_id, await self.get_player_number(loser))
        # it's now winner player's turn
        await self.set_new_turn(self.game_id, await self.get_player_number(winner))

        await self.verify_or_revoke_victory(self.game_id)
        await self.empty_stacked_cards(self.game_id)

        event_specifics = {
            'type': 'doubt',
            'who_doubted': await self.get_player_name(who_doubted),
            'who_doubted_number': await self.get_player_number(who_doubted),
            'who_was_doubted': await self.get_player_name(last_player),
            'outcome': outcome,
            'whole_stack': whole_stack,
            'copies_removed': copies_removed,
            'losing_player': await self.get_player_name(loser),
        }

        await self.send_new_state_to_all_players(event_specifics)
        await self.unlock_game(self.game_id)  # resume normal game flow
        await self.check_current_player_online()  # handle the case where current player isn't online

    
    async def place_cards(self, cards):
        # Sends amount of cards of current number placed and saves placed cards to db

        if await self.check_card_possession(self.game_id, self.player_id, cards):
            # player is illegally trying to play cards they don't have
            return
        
        if await self.is_locked(self.game_id):
            # someone else got here first
            return

        if await self.get_current_turn(self.game_id) != await self.get_player_number(self.player_id):
            # wrong player trying to play
            return
        
        if not len(cards):
            # trying to place 0 cards
            return
        
        await self.lock_game(self.game_id)  # prevent further action from other players

        # place selected cards onto the stack and remove them from user's hand
        await self.remove_from_hand(self.game_id, self.player_id, cards)
        await self.add_stacked_cards(self.game_id, cards)

        # if there was a player eligible for winning, check they still have zero cards
        await self.verify_or_revoke_victory(self.game_id)

        if not await self.get_number_of_cards_in_hand(self.player_id):  # player has no more cards
            await self.set_winning_player(self.game_id, await self.get_player_number(self.player_id))

        # contains information specific to this type of event that will be used by the client
        # to play the corresponding animations
        event_specifics = {
            'type': 'cards_placed',
            'by_who': await self.get_player_number(self.player_id),
            'number_of_cards_placed': len(cards), 
        }

        await self.increment_turn(self.game_id)
        await self.send_new_state_to_all_players(event_specifics)
        await self.unlock_game(self.game_id)  # resume normal game flow
        await self.check_current_player_online()  # handle the case where current player isn't online

    async def send_reaction(self, reaction):
        # Called when a player clicks on a reaction button
        if reaction not in ['laughing', 'crying', 'drunk', 'smirk', 'thinking', 'angry']: 
            # only allow supported emojis
            return

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'reaction_handler',
                'who': self.player_id,
                'reaction': reaction,
            }
        )

    async def verify_or_revoke_victory(self, game_id):
        # if there was a player with zero cards on last turn, and they
        # still have zero cards after next event, they win
        winning_player = await self.get_winning_player(self.game_id)
        if winning_player != -1:
            winning_player_id = await self.get_player_id_from_number(self.game_id, winning_player)
            if not await self.get_number_of_cards_in_hand(winning_player_id):
                event_specifics = {
                    'type': 'player_won',
                    'winner': await self.get_player_name(winning_player_id),
                }
                await self.send_new_state_to_all_players(event_specifics)
                await self.set_game_has_been_won(self.game_id)
                await self.lock_game(self.game_id)
            else:
                # if player now has more than 0 cards, they aren't eligible for winning anymore
                await self.set_winning_player(self.game_id, -1)

    # HANDLERS
    async def game_state_handler(self, event):
        if(self.player_id != event['player_id']):
            return
        state = await self.get_game_state(self.game_id, event['player_id'])
        await self.send(text_data=json.dumps({
            'type': 'new_state',
            'state': state,
            'event_specifics': event['event_specifics'],
        }))

    async def reaction_handler(self, event):
        if(self.player_id == event['who']):
            # don't send reaction back to the player who sent the event
            return

        await self.send(text_data=json.dumps({
            'event_specifics': {
                'type': 'reaction',
                'reaction': event['reaction'],
                'who': await self.get_player_number(event['who']),
            },
        }))

    @database_sync_to_async
    def increment_turn(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.player_last_turn = game.player_current_turn
        game.player_current_turn = (game.player_current_turn % game.number_of_players) + 1
        game.save()

    @database_sync_to_async
    def pass_turn(self, game_id):
        # increments turn but doesn't update player_last_turn 
        # (used for skipping turns of offline players)
        game = Game.objects.get(pk=game_id)
        game.player_current_turn = (game.player_current_turn % game.number_of_players) + 1
        game.save()

    @database_sync_to_async
    def get_hand(self, player_id):
        cards = CardsInHand.objects.filter(player_id=player_id)
        return list(cards.values('card_seed', 'card_number'))

    @database_sync_to_async
    def is_locked(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.locked

    @database_sync_to_async
    def lock_game(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.locked = True
        game.save()

    @database_sync_to_async
    def unlock_game(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.locked = False
        game.save()

    @database_sync_to_async
    def get_current_turn(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.player_current_turn

    @database_sync_to_async
    def get_player_last_turn(self, game_id):  # returns id of last player who put down cards
        game = Game.objects.get(pk=game_id)
        num = game.player_last_turn

        try:
            player = Player.objects.get(game_id=game_id, player_number=num)
            return player.pk
        except Player.DoesNotExist:
            return None

    @database_sync_to_async
    def set_new_turn(self, game_id, new_turn):  # sets new turn to a given number
        game = Game.objects.get(pk=game_id)
        game.player_last_turn = game.player_current_turn
        game.player_current_turn = new_turn
        game.save()

    @database_sync_to_async
    def get_stacked_cards(self, game_id, amount=0):  # get a list of the cards that are on the stack
        game = Game.objects.get(pk=game_id)
        selected_cards = json.loads(game.stacked_cards)[-amount:]
        if selected_cards == []:
            return None
        return selected_cards

    @database_sync_to_async
    def empty_stacked_cards(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.stacked_cards = "[]"
        game.save()

    @database_sync_to_async
    def set_stacked_cards(self, game_id, cards):
        game = Game.objects.get(pk=game_id)
        game.stacked_cards = json.dumps(cards)
        game.last_amount_played = len(cards)
        game.save()

    @database_sync_to_async
    def add_stacked_cards(self, game_id, cards):  # adds a list of cards to the stack
        game = Game.objects.get(pk=game_id)
        stack = json.loads(game.stacked_cards)
        stack.extend(cards)
        game.stacked_cards = json.dumps(stack)
        game.last_amount_played = len(cards)
        game.save()

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
        game.save()

    @database_sync_to_async
    def check_card_possession(self, game_id, player_id, cards): 
        # returns 0 if the requested player has all the requested cards in their hand, 1 otherwise
        cards_counted = {}
        for card in cards:
            # build a dictionary where to each card code corresponds the
            # amount of that card the player wants to place down
            split_card_str = list(card)  # split each character
            seed = split_card_str[len(split_card_str)-1]  # get last character for seed
            number = card[:-1]  # remaining characters are the number
            card_str = str(number + seed)
            if card_str not in cards_counted:
                cards_counted[card_str] = 1
            else:
                cards_counted[card_str] = cards_counted[card_str] + 1

        for card in cards:
            # for every card, see if the number of times it appear is greater than
            # the number of copies of it the player has in their hand
            split_card_str = list(card)  # split each character
            seed = split_card_str[len(split_card_str)-1]  # get last character for seed
            number = card[:-1]  # remaining characters are the number
            if CardsInHand.objects.filter(Q(player_id=player_id) & Q(card_seed=seed) & Q(card_number=int(number))).count() < cards_counted[str(number + seed)]:
                return 1
        return 0

    @database_sync_to_async
    def remove_from_hand(self, game_id, player_id, cards):
        for card in cards:
            split_card_str = list(card)  # split each character
            seed = split_card_str[len(split_card_str) - 1]  # get last character for seed
            number = int(card[:-1])  # remaining characters are the number
            card_in_hand = CardsInHand.objects.filter(Q(player_id=player_id) & Q(card_seed=seed) & Q(card_number=number))[0]
            card_in_hand.delete()

    @database_sync_to_async
    def add_to_hand(self, game_id, player_id, cards):
        for card in cards:
            split_card_str = list(card)  # split each character
            seed = split_card_str[len(split_card_str)-1]  # get last character for seed
            number = int(card[:-1])  # remaining characters are the number

            card_in_hand = CardsInHand(card_seed=seed, card_number=number, player_id=Player.objects.get(pk=player_id))
            card_in_hand.save()

    @database_sync_to_async
    def get_player_number(self, player_id):
        player = Player.objects.get(pk=player_id)
        return player.player_number

    @database_sync_to_async
    def get_player_id_from_number(self, game_id, player_num):
        try:
            return Player.objects.get(Q(game_id=game_id) & Q(player_number=player_num)).pk
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
    def has_begun(self, game_id):
        return Game.objects.get(pk=game_id).has_begun

    @database_sync_to_async
    def begin_game(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.has_begun = True
        game.save()

    @database_sync_to_async
    def get_amount_of_card_in_hand(self, player_id, card_number):
        length = len(CardsInHand.objects.filter(Q(player_id=player_id) & Q(card_number=card_number)))
        logging.warning(card_number + " " + str(length))
        return length

    @database_sync_to_async
    def remove_all_cards(self, player_id, card_number):
        cards = CardsInHand.objects.filter(Q(player_id=player_id) & Q(card_number=card_number))
        for card in cards:
            card.delete()

    @database_sync_to_async
    def set_winning_player(self, game_id, player_number):
        game = Game.objects.get(pk=game_id)
        game.winning_player = player_number
        game.save()

    @database_sync_to_async
    def get_winning_player(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.winning_player

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
                'number': player.player_number,
                'is_online': player.is_online,
                'number_of_cards': CardsInHand.objects.filter(player_id=player).count(),
                'name': player.name,
            }
            other_players_list.append(player_data)
        state = {
            'current_turn': game.player_current_turn,
            'last_turn': game.player_last_turn,
            'current_card': game.current_card,
            'last_card': game.last_card,
            'number_of_stacked_cards': len(json.loads(game.stacked_cards)),
            'last_amount_played': game.last_amount_played,
            'won_by': game.winning_player if game.has_been_won else -1,
            'my_cards': my_cards,
            'other_players_data': other_players_list,
            'my_player_number': this_player.player_number,
        }

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
        player = Player.objects.get(pk=player_id)
        player.is_online = value
        if value and player.has_left:
            player.has_left = False
        player.save()

    @database_sync_to_async
    def set_has_left(self, player_id):
        player = Player.objects.get(pk=player_id)

        player.has_left = True
        player.save()

    @database_sync_to_async
    def set_game_has_been_won(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.has_been_won = True
        game.save()
