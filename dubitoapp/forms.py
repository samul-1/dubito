from django import forms

class GameForm(forms.Form):
    CHOICES = (
        ('2','2'),
        ('3','3'),
        ('4','4'),
        ('5','5'),
        ('6','6'),
        ('7','7'),
        ('8','8'),
        ('9','9'),
        ('10','10'),
    )

    number_of_players = forms.ChoiceField(label="Numero di giocatori", required=True, choices=CHOICES)
    creator_name = forms.CharField(label="Il tuo nome", required=True, max_length=50)

class JoinForm(forms.Form):
    code = forms.CharField(label="Codice partita", required=True, max_length=5)
    name = forms.CharField(label="Il tuo nome", required=True, max_length=50)