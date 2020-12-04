from django import forms

class GameForm(forms.Form):
    CHOICES = (
        ('2','2'),
        ('3','3'),
        ('4','4'),
        ('5','5'),
        ('6','6'),
    )

    number_of_players = forms.ChoiceField(label="Numero di giocatori", required=True, choices=CHOICES)
    creator_name = forms.CharField(label="Il tuo nome", required=True, max_length=50, widget=forms.TextInput(attrs={"autocomplete":"off" }))

class JoinForm(forms.Form):
    code = forms.CharField(label="Codice partita", required=True, max_length=5, widget=forms.TextInput(attrs={"autocomplete":"off", "type":"number"}))
    name = forms.CharField(label="Il tuo nome", required=True, max_length=50, widget=forms.TextInput(attrs={"autocomplete":"off" }))