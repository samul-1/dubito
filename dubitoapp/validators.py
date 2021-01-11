from django.core.exceptions import ValidationError
from .models import Game
from django.utils.translation import gettext as _


def validate_gamecode(value):
    # raises ValidationError if the input gamecode doesn't correspond to
    # an existing game, or if the corresponding game has already begun
    msg = ""
    try:
        game = Game.objects.get(code=value)
        if game.joined_players == game.number_of_players:
            msg = _("La partita è al completo.")
    except Exception:
        msg = _("Partita non trovata.")

    if msg != "":
        raise ValidationError(msg)

def validate_number_of_players(value):
    if int(value) < 2 or int(value) > 6:
        raise ValidationError(_("I giocatori devono essere da 2 a 6."))
