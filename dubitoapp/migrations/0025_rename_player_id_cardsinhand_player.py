# Generated by Django 4.2.7 on 2023-11-29 19:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dubitoapp', '0024_alter_game_stacked_cards'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cardsinhand',
            old_name='player_id',
            new_name='player',
        ),
    ]