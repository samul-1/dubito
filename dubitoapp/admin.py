from django.contrib import admin
from .models import Game, Player, CardsInHand

class GameAdmin(admin.ModelAdmin):
    list_display = ('pk', 'code', 'number_of_players', 'joined_players', 'player_current_turn', 'player_last_turn')

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('game_id', 'name', 'player_number', 'pk')

class CardsInHandAdmin(admin.ModelAdmin):
    list_display = ('player_id', 'card_seed', 'card_number', 'pk')

admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(CardsInHand, CardsInHandAdmin)