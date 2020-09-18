# Generated by Django 3.1.1 on 2020-09-17 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dubitoapp', '0006_game_has_begun'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='has_been_won',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='game',
            name='winning_player',
            field=models.IntegerField(default=-1),
        ),
        migrations.AlterField(
            model_name='game',
            name='current_card',
            field=models.IntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='last_card',
            field=models.IntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='player_last_turn',
            field=models.IntegerField(default=-1, null=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='stacked_cards',
            field=models.CharField(default='[]', max_length=300),
        ),
    ]
