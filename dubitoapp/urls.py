from django.urls import path, include, re_path

from . import views

urlpatterns = [
    path('', views.create_new_game, name='index'),
    path('create', views.create_new_game, name='create_game'),
    path('join_game', views.join_game),
    path('feedback', views.feedback_create, name='add_feedback'),
    re_path(r'^game/(?P<game_id>\d+)/$', views.game, name='game'),
    re_path(r'^get_joined_players/(?P<game_id>\d+)/$', views.get_joined_players),
]
