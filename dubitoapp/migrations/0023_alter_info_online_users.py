# Generated by Django 4.2.7 on 2023-11-28 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dubitoapp', '0022_game_coutdown_end'),
    ]

    operations = [
        migrations.AlterField(
            model_name='info',
            name='online_users',
            field=models.PositiveIntegerField(default=0),
        ),
    ]