import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging
from channels.db import database_sync_to_async
import asyncio
from .models import Game, Player, CardsInHand
from django.db.models import Q
from asgiref.sync import sync_to_async


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.player_id = self.scope['session']['player_id']
        self.game_group_name = 'game_%s' % self.game_id

        # Join room group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        # # Send message to the player with their cards
        # await self.channel_layer.group_send(
        #     self.game_group_name,
        #     {
        #         'type': 'give_cards_handler',
        #         'destination': self.player_id,
        #     }
        # )

        # Send message to everybody about the player entering and how many cards they have
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'player_joined_handler',
                'player_id': self.player_id,
                'number_of_cards': await self.get_number_of_cards_in_hand(self.player_id),
            }
        )

        stack = await self.get_stacked_cards(self.game_id)
        stacked_cards = len(stack)

        # Send message to user who joined to get info about other players
        for player in await sync_to_async(list)(Player.objects.filter(Q(game_id=self.game_id))):
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'player_info_handler',
                    'player_id': player.pk,
                    'number_of_cards': await self.get_number_of_cards_in_hand(player.pk),
                    'dest': self.player_id,
                    'stacked_cards': stacked_cards,
                }
            )
                    # Send message to the player with their cards
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'give_cards_handler',
                    'destination': player.pk,
                }
            )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json['type']
        game_id = self.scope['url_route']['kwargs']['game_id']

        
        logging.warning("curr turn " + str(await self.get_current_turn(game_id)))
        logging.warning(action)
        if action == 'start_round': # called when the first player places down card(s) and initiates a round
            claimed_card = text_data_json['claimed']
            cards = text_data_json['cards']
            await self.start_round(claimed_card, cards)
        if action == 'doubt': # called when a player interrupts game to doubt
            await self.doubt()
        if action == 'place_cards': # called when a player places down card(s)
            cards = text_data_json['cards']
            await self.place_cards(cards)
        
        logging.warning("new turn " + str(await self.get_current_turn(game_id)))

    async def start_round(self, claimed_card, cards):
        # Sends claimed card information and saves actually placed cards to db
        game_id = self.scope['url_route']['kwargs']['game_id']

        if await self.is_locked(game_id): # see if someone else got here first
            logging.warning("locked")
            return

        # wrong player trying to play
        if await self.get_current_turn(game_id) != await self.get_player_number(self.scope['session']['player_id']):
            return

        # trying to place 0 cards
        if not len(cards):
            logging.warning("trying to place zero cards")
            return

        # You can't start two consecutive rounds with the same card
        if int(claimed_card) == await self.get_current_card(self.scope['url_route']['kwargs']['game_id']):
            logging.warning("!")
            return
        
        await self.lock_game(game_id) # prevent further action from other players

        await self.set_current_card(game_id, claimed_card)
        await self.set_stacked_cards(game_id, cards)
        await self.remove_from_hand(game_id, self.scope['session']['player_id'], cards)
        
        if not await self.get_number_of_cards_in_hand(self.scope['session']['player_id']): # player has no more cards
            await self.set_winning_player(game_id, await self.get_player_number(self.scope['session']['player_id']))

        # DB WORK HERE

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'start_round_handler',
                'claimed': claimed_card,
                'number': len(cards),
            }
        )
        await self.increment_turn(game_id)
        await self.unlock_game(game_id) # resume normal game flow
    
    async def doubt(self):
        # Doubts
        game_id = self.scope['url_route']['kwargs']['game_id']

        if await self.is_locked(game_id): # see if someone else got here first
            logging.warning("locked")
            return

        if self.scope['session']['player_id'] == await self.get_player_last_turn(game_id): # player doubted themselves
            logging.warning("doubted themselves")
            return
        
        await self.lock_game(game_id) # prevent further action from other players
        
        # get last cards played from the stack
        uncovered_cards = await self.get_stacked_cards(
            game_id,
            await self.get_last_amount_played(game_id)
        )
        outcome = 0

        # compare cards against claimed card
        for card in uncovered_cards:
            split_card_str = list(card) # split each character
            number = int(card[:-1]) # remaining characters are the number
            claimed_card = await self.get_current_card(game_id)
            logging.warning("uncovered " + str(number) + ", claimed " + str(claimed_card))
            if(number != claimed_card and number != 14): # 14 is the joker
                outcome = 1
                break
        
        whole_stack = await self.get_stacked_cards(game_id)
        who_doubted = self.scope['session']['player_id']
        last_player = await self.get_player_last_turn(game_id)

        if(outcome): # add whole stack to doubted player's hand, and it's now doubter's turn
            await self.add_to_hand(game_id, last_player, whole_stack)
            for i in range(1, 14):
                if await self.get_amount_of_card_in_hand(last_player, str(i)) == 8: # if they have 8 copies of a card, discard those
                    await self.remove_all_cards(last_player, str(i))
                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {
                            'type': 'copies_removed_handler',
                            'from': await self.get_player_number(last_player),
                        }
                    )
                    logging.warning("sent")
            await self.set_new_turn(game_id, await self.get_player_number(who_doubted))
        else: # add whole stack to doubter, and it's now doubted player's turn
            await self.add_to_hand(game_id, who_doubted, whole_stack)
            for i in range(1, 14):
                if await self.get_amount_of_card_in_hand(who_doubted, str(i)) == 8: # if they have 8 copies of a card, discard those
                    await self.remove_all_cards(who_doubted, str(i))
                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {
                            'type': 'copies_removed_handler',
                            'from': await self.get_player_number(who_doubted),
                        }
                    )
                    logging.warning("sent")
            await self.set_new_turn(game_id, await self.get_player_number(last_player))

        await self.empty_stacked_cards(game_id)

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'doubt_handler',
                'who_doubted': await self.get_player_number(who_doubted),
                'outcome': outcome, # 0 if failed, 1 if successful for doubter,
                'uncovered_cards': uncovered_cards,
                'whole_stack': whole_stack,
            }
        )
        
        await self.unlock_game(game_id) # resume normal game flow

    
    async def place_cards(self, cards):
        # Sends amount of cards of alleged type placed and saves actually placed cards to db
        game_id = self.scope['url_route']['kwargs']['game_id']
        
        if await self.is_locked(game_id): # see if someone else got here first
            logging.warning("locked")
            return

        # wrong player trying to play
        if await self.get_current_turn(game_id) != await self.get_player_number(self.scope['session']['player_id']):
            logging.warning("wrong turn")
            return
        
        # trying to place 0 cards
        if not len(cards):
            logging.warning("trying to place zero cards")
            return
        
        await self.lock_game(game_id) # prevent further action from other players

        await self.remove_from_hand(game_id, self.scope['session']['player_id'], cards)
        await self.add_stacked_cards(game_id, cards)
        
        if not await self.get_number_of_cards_in_hand(self.scope['session']['player_id']): # player has no more cards
            await self.set_winning_player(game_id, await self.get_player_number(self.scope['session']['player_id']))

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'place_cards_handler',
                'number': len(cards),
            }
        )
        await self.increment_turn(game_id)
        await self.unlock_game(game_id) # resume normal game flow



    # HANDLERS

    async def give_cards_handler(self, event):
        if(self.scope['session']['player_id'] == event['destination']):
            cards = await self.get_hand(self.scope['session']['player_id'])
            await self.send(text_data=json.dumps({
                'type': 'get_initial_hand',
                'cards': cards,
            }))

    async def start_round_handler(self, event):
        claimed = event['claimed']
        number = event['number']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'round_start',
            'claimed': claimed,
            'number': number,
        }))

    async def copies_removed_handler(self, event):
        from_p = event["from"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'copies_removed',
            'from': from_p,
        }))

    
    async def doubt_handler(self, event):
        who_doubted = event['who_doubted']
        outcome = event['outcome']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'doubt',
            'who_doubted': who_doubted,
            'outcome': outcome,
            'uncovered_cards': event['uncovered_cards'],
            'whole_stack': event['whole_stack'],
        }))
    
    async def place_cards_handler(self, event):
        number = event['number']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'cards_placed',
            'number': number,
        }))

    
    async def player_joined_handler(self, event):
        if self.scope['session']['player_id'] != event['player_id']:
            player_number = await self.get_player_number(event['player_id'])
            player_name = await self.get_player_name(event['player_id'])

            # Send message to WebSocket
            await self.send(text_data=json.dumps({
                'type': 'player_joined',
                'player_number': player_number,
                'player_name': player_name,
                'number_of_cards': event['number_of_cards'],
            }))
    
    async def player_info_handler(self, event):
        if self.scope['session']['player_id'] != event['dest']: # only send info to the player who joined
            return
        if self.scope['session']['player_id'] != event['player_id']:
            player_number = await self.get_player_number(event['player_id'])
            player_name = await self.get_player_name(event['player_id'])

            # Send message to WebSocket
            await self.send(text_data=json.dumps({
                'type': 'player_info',
                'player_number': player_number,
                'player_name': player_name,
                'number_of_cards': event['number_of_cards'],
                'stacked_cards': event['stacked_cards']
            }))

    @database_sync_to_async
    def increment_turn(self, game_id):
        game = Game.objects.get(pk=game_id)
        game.player_last_turn = game.player_current_turn
        game.player_current_turn = (game.player_current_turn % game.number_of_players) + 1
        game.save()

    @database_sync_to_async
    def get_hand(self, player_id):
        cards = CardsInHand.objects.filter(player_id=player_id)
        return list(cards.values('card_seed','card_number'))

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
    def get_player_last_turn(self, game_id): # returns id of last player who put down cards
        game = Game.objects.get(pk=game_id)
        num = game.player_last_turn

        player = Player.objects.get(game_id=game_id, player_number=num)
        return player.pk
    
    @database_sync_to_async
    def set_new_turn(self, game_id, new_turn): # sets new turn to a given number
        game = Game.objects.get(pk=game_id)
        game.player_last_turn = game.player_current_turn
        game.player_current_turn = new_turn
        game.save()
    
    @database_sync_to_async
    def get_stacked_cards(self, game_id, amount=0): # get a list of the cards that are down on the table
        game = Game.objects.get(pk=game_id)
        selected_cards = json.loads(game.stacked_cards)[-amount:]
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
    def add_stacked_cards(self, game_id, cards): # adds a list of cards to those in play
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
    def remove_from_hand(self, game_id, player_id, cards):
        for card in cards:
            split_card_str = list(card) # split each character
            seed = split_card_str[len(split_card_str)-1] # get last character for seed
            number = int(card[:-1]) # remaining characters are the number
            # logging.warning("removing " + str(number) + seed + " from player " + str(player_id))
            try:
                card_in_hand = CardsInHand.objects.filter(Q(player_id=player_id) & Q(card_seed=seed) & Q(card_number=number))[0]
                card_in_hand.delete()
            except:
                pass
    
    @database_sync_to_async
    def add_to_hand(self, game_id, player_id, cards):
        for card in cards:
            split_card_str = list(card) # split each character
            seed = split_card_str[len(split_card_str)-1] # get last character for seed
            number = int(card[:-1]) # remaining characters are the number

            card_in_hand = CardsInHand()
            card_in_hand.card_seed = seed
            card_in_hand.card_number = number
            card_in_hand.player_id = Player.objects.get(pk=player_id)
            card_in_hand.save()

    @database_sync_to_async
    def get_player_number(self, player_id):
        player = Player.objects.get(pk=player_id)
        return player.player_number

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