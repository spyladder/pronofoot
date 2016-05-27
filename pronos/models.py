# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from __future__ import unicode_literals

from django.db import models
from django.conf import settings

class Cups(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    cup_name = models.CharField(max_length=30, blank=True, null=True)
    cup_year = models.TextField(blank=True, null=True)  # This field type is a guess.

    def __str__(self):
        return self.cup_name

    class Meta:
        db_table = 'Cups'


class Matches(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    team_a = models.ForeignKey('Teams', models.DO_NOTHING, related_name='match_team_a', db_column='team_A')  # Field name made lowercase.
    team_b = models.ForeignKey('Teams', models.DO_NOTHING, related_name='match_team_b', db_column='team_B')  # Field name made lowercase.
    score_a = models.SmallIntegerField(db_column='score_A')  # Field name made lowercase.
    score_b = models.SmallIntegerField(db_column='score_B')  # Field name made lowercase.
    score_prolong_a = models.SmallIntegerField(db_column='score_prolong_A', blank=True, null=True)  # Field name made lowercase.
    score_prolong_b = models.SmallIntegerField(db_column='score_prolong_B', blank=True, null=True)  # Field name made lowercase.
    score_tab_a = models.SmallIntegerField(db_column='score_tab_A', blank=True, null=True)  # Field name made lowercase.
    score_tab_b = models.SmallIntegerField(db_column='score_tab_B', blank=True, null=True)  # Field name made lowercase.
    cup = models.ForeignKey(Cups, models.DO_NOTHING, db_column='cup')
    phase = models.CharField(max_length=15, blank=True, null=True)
    match_date = models.DateField(blank=True, null=True)

    def getFullScore(self, team):
        if team == 'a':
            if self.score_prolong_a == None:
                return self.score_a
            else:
                return self.score_a + self.score_prolong_a
        else:
            if self.score_prolong_b == None:
                return self.score_b
            else:
                return self.score_b + self.score_prolong_b

    def getWinnerTeam(self):
        # If it's a match with no prolongation
        if self.score_prolong_a == None:
            if self.score_a > self.score_b:
                return 'a'
            elif self.score_a < self.score_b:
                return 'b'
            else:
                return 'd' # Draw
        else: # Match with prolongation
            # If match ended without penalties
            if self.score_tab_a == None:
                if self.score_a + self.score_prolong_a > self.score_b + self.score_prolong_b:
                    return 'a'
                else:
                    return 'b'
            else: # Match ended with penalties
                if self.score_tab_a > self.score_tab_b:
                    return 'a'
                else:
                    return 'b'

    def __str__(self):
        spa, spb = 0, 0
        if self.score_prolong_a != None:
            spa = self.score_prolong_a
        if self.score_prolong_b != None:
            spb = self.score_prolong_b
        return '{}_{}_{}_{}-{}_{}'.format(
            self.match_date, self.phase, self.team_a, self.score_a + spa,
            self.score_b + spb, self.team_b)

    class Meta:
        db_table = 'Matches'


class Teams(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    team_name = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return self.team_name

    class Meta:
        db_table = 'Teams'


class TeamsByCup(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    team = models.ForeignKey(Teams, models.DO_NOTHING, db_column='team')
    cup = models.ForeignKey(Cups, models.DO_NOTHING, db_column='cup')
    fifa_rank = models.SmallIntegerField(blank=True, null=True)

    def __str__(self):
        return '{}_{}_{}'.format(self.team, self.cup, self.fifa_rank)

    class Meta:
        db_table = 'Teams_by_cup'


class Pronostics(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_column='user')
    match = models.ForeignKey(Matches, db_column='match_id')
    score_a = models.SmallIntegerField(blank=True, null=True)
    score_b = models.SmallIntegerField(blank=True, null=True)
    score_prolong_a = models.SmallIntegerField(blank=True, null=True)
    score_prolong_b = models.SmallIntegerField(blank=True, null=True)
    tab_winner = models.CharField(max_length=1, blank=True, null=True)

    def __str__(self):
        return '{}_{}'.format(self.user, self.match)

    class Meta:
        db_table = 'Pronostics'
