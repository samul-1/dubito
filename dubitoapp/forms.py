from django import forms
from django.forms import ModelForm, Textarea
from .validators import validate_gamecode, validate_number_of_players
from .models import Feedback

class GameForm(forms.Form):
    CHOICES = (
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
    )
    number_of_players = forms.ChoiceField(
        label="Numero di giocatori",
        required=True,
        choices=CHOICES,
        widget=forms.RadioSelect(attrs={"class": "inline-styleless-radio"}),
        validators=[validate_number_of_players]
    )
    creator_name = forms.CharField(
        label="Il tuo nome",
        required=True, max_length=10,
        widget=forms.TextInput(attrs={"autocomplete": "off"})
    )

class JoinForm(forms.Form):
    code = forms.CharField(
        label="Codice partita",
        required=True,
        max_length=5,
        widget=forms.TextInput(attrs={"autocomplete": "off", "type": "number"}),
        validators=[validate_gamecode]
    )
    name = forms.CharField(
        label="Il tuo nome",
        required=True,
        max_length=10,
        widget=forms.TextInput(attrs={"autocomplete": "off"})
    )

class FeedbackForm(ModelForm):
    class Meta:
        model = Feedback
        fields = ['sender_name', 'email', 'message']
        widgets = {
            'message': Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(FeedbackForm, self).__init__(*args, **kwargs)
        self.fields["sender_name"].required = True
        self.fields["email"].required = False
        self.fields["message"].required = True
