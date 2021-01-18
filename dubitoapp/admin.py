from django.contrib import admin
from .models import Game, Player, CardsInHand, Feedback, Info


class GameAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "code",
        "number_of_players",
        "timestamp",
        "joined_players",
        "player_current_turn",
        "player_last_turn",
    )


class PlayerAdmin(admin.ModelAdmin):
    list_display = ("game_id", "name", "player_number", "pk")


class CardsInHandAdmin(admin.ModelAdmin):
    list_display = ("player_id", "card_seed", "card_number", "pk")


class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("pk", "sender_name", "email", "message", "timestamp")


class InfoAdmin(admin.ModelAdmin):
    list_display = ("pk", "online_users")


admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(CardsInHand, CardsInHandAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(Info, InfoAdmin)
