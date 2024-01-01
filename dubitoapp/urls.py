from django.urls import path, include, re_path

# from django.conf.urls import url
# from django.views.i18n import JavaScriptCatalog
# from django.conf.urls.i18n import i18n_patterns

from . import views


urlpatterns = [
    path("", views.create_new_game, name="index"),
    path("create", views.create_new_game, name="create_game"),
    path("join_game", views.join_game, name="join_game"),
    path("feedback", views.feedback_create, name="add_feedback"),
    path("trigger_error", views.trigger_error, name="trigger_error"),
    re_path(r"^game/(?P<game_id>\d+)/$", views.game, name="game"),
    re_path(r"^get_joined_players/(?P<game_id>\d+)/$", views.get_joined_players),
]
