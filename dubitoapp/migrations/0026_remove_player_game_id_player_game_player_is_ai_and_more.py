# Generated by Django 4.2.7 on 2023-12-05 10:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dubitoapp', '0025_rename_player_id_cardsinhand_player'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='player',
            name='game_id',
        ),
        migrations.AddField(
            model_name='player',
            name='game',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='players', to='dubitoapp.game'),
        ),
        migrations.AddField(
            model_name='player',
            name='is_ai',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='cardsinhand',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cards', to='dubitoapp.player'),
        ),
    ]