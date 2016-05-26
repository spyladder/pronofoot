# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-20 17:11
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pronos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pronostics',
            fields=[
                ('id', models.SmallIntegerField(primary_key=True, serialize=False)),
                ('score_a', models.SmallIntegerField(blank=True, null=True)),
                ('score_b', models.SmallIntegerField(blank=True, null=True)),
                ('score_prolong_a', models.SmallIntegerField(blank=True, null=True)),
                ('score_prolong_b', models.SmallIntegerField(blank=True, null=True)),
                ('tab_winner', models.CharField(blank=True, max_length=1, null=True)),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pronos.Matches')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'Pronostics',
            },
        ),
    ]