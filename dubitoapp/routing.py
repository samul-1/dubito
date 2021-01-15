from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/play/(?P<game_id>\d+)/$', consumers.GameConsumer.as_asgi()),
    re_path(r'ws/matchmaking/(?P<player_name>\w+)/$', consumers.MatchmakingConsumer.as_asgi()),

]