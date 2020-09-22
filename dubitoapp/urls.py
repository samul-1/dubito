from django.urls import path, include, re_path

from . import views

urlpatterns = [
    path('', views.create_new_game, name='index'),
    path('create_game', views.create_new_game, name="create_game"),
    #re_path(r'^join_game/(?P<game_id>\d+)/$', views.join_game, name='join_game'),
    path('check_session', views.check_session),
    path('join_game', views.join_game),
    re_path(r'^game/(?P<game_id>\d+)/$', views.game, name='game'),
    re_path(r'^get_joined_players/(?P<game_id>\d+)/$', views.get_joined_players),
    path('test', views.test),
]