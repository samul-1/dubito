# Generated by Django 3.1.1 on 2020-09-12 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dubitoapp', '0004_auto_20200912_1503'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='player_number',
            field=models.IntegerField(default=1),
        ),
    ]
