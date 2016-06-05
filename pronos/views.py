from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
from django.http import Http404
from django.http import HttpResponse
from django.template import loader
from django.db.models import Q, F
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.forms import formset_factory
from pronos.models import *
from pronos.forms import *
import datetime
import json

U_COLORS = {
    'light': ['#8bf', '#8fb', '#b8f', '#f8b', '#bf8', '#fb8'],
    'dark':  ['#69d', '#6d9', '#96d', '#d69', '#9d6', '#d96']
}
GREY = { 'light': '#eee', 'dark': '#ccc'}

def index(request):
    cup_list = Cups.objects.order_by('-cup_year')
    context = {
        'cup_list': cup_list,
    }
    return render(request, 'pronos/index.html', context)


def cup(request, cup_id):
    cup = get_object_or_404(Cups, pk=cup_id)
    cup_name = cup.cup_name
    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
    }
    return render(request, 'pronos/cup.html', context)


def cupTeams(request, cup_id):
    team_list = TeamsByCup.objects.filter(cup=cup_id).order_by('fifa_rank')
    if not team_list:
        raise Http404("Pas d'équipe disponible.")
    cup_name = team_list[0].cup
    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
        'team_list': team_list,
    }
    return render(request, 'pronos/teams_by_cup.html', context)


def matches(request, cup_id):
    match_list = Matches.objects.filter(cup=cup_id).order_by('match_date')
    if not match_list:
        raise Http404("Pas de match disponible.")
    cup_name = match_list[0].cup
    phases = getFormatedMatchList(match_list)
    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
        'phases': phases,
    }
    return render(request, 'pronos/matches.html', context)


def stats(request, cup_id):
    match_list = Matches.objects.filter(
        cup=cup_id,
        match_date__lt=datetime.date.today()
    )
    cup_name = Cups.objects.get(pk=cup_id)
    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
    }
    if not match_list:
        return render(request, 'pronos/stats.html', context)

    nb_goals = 0
    nb_draws = 0
    nb_matches_won_by_favorite = 0
    scores_dict = {}
    for match in match_list:
        score_a = match.getFullScore('a')
        score_b = match.getFullScore('b')
        score = ""
        if score_a > score_b:
            score = str(score_a) + '-' + str(score_b)
        else:
            score = str(score_b) + '-' + str(score_a)

        if score in scores_dict:
            scores_dict[score] += 1
        else:
            scores_dict[score] = 1

        nb_goals += score_a + score_b
        if score_a == score_b:
            nb_draws += 1

        team_a = TeamsByCup.objects.filter(team=match.team_a, cup=match.cup)
        team_b = TeamsByCup.objects.filter(team=match.team_b, cup=match.cup)
        if len(team_a) > 0 and len(team_b) > 0:
            rank_a = team_a[0].fifa_rank
            rank_b = team_b[0].fifa_rank
            if rank_a < rank_b and score_a > score_b or rank_a > rank_b and score_a < score_b:
                nb_matches_won_by_favorite += 1

    nb_matches_total = len(match_list)
    goals_per_match = nb_goals / nb_matches_total
    draw_percent = 100 * nb_draws / nb_matches_total

    score_list_sorted = sorted(scores_dict.items(), key=lambda t: t[1], reverse=True)
    score_list_percent = []
    for score in score_list_sorted:
        score_list_percent.append((score[0], score[1], 100 * score[1] / nb_matches_total))

    matches_won_by_favorite_percent = 100 * nb_matches_won_by_favorite / nb_matches_total
    matches_lost_by_favorite_percent = 100 - matches_won_by_favorite_percent - draw_percent

    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
        'nb_goals': nb_goals,
        'goals_per_match': goals_per_match,
        'draw_percent': draw_percent,
        'matches_won_by_favorite_percent': matches_won_by_favorite_percent,
        'matches_lost_by_favorite_percent': matches_lost_by_favorite_percent,
        'score_list_percent': score_list_percent,
    }
    return render(request, 'pronos/stats.html', context)


def team(request, cup_id, team_id):
    team = get_object_or_404(Teams, pk=team_id)
    team_name = team.team_name

    match_list = Matches.objects.filter(
        Q(cup=cup_id),
        Q(team_a=team_id) | Q(team_b=team_id),
        Q(match_date__lt=datetime.date.today())
    ).order_by('match_date')

    if not match_list:
        raise Http404("Pas de match disponible.")

    nb_goals_plus = 0
    nb_goals_minus = 0
    for match in match_list:
        if match.team_a.id == int(team_id):
            nb_goals_plus += match.getFullScore('a')
            nb_goals_minus += match.getFullScore('b')
        else:
            nb_goals_plus += match.getFullScore('b')
            nb_goals_minus += match.getFullScore('a')
    goals_diff = nb_goals_plus - nb_goals_minus

    phases = getFormatedMatchList(match_list)
    cup_name = match_list[0].cup
    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
        'team_name': team_name,
        'phases': phases,
        'nb_goals_plus': nb_goals_plus,
        'nb_goals_minus': nb_goals_minus,
        'goals_diff': goals_diff,
    }
    return render(request, 'pronos/team.html', context)


def getFormatedMatchList(match_list):
    phases = []
    dates = []
    matches = []
    cur_phase = ""
    cur_date = 0
    for match in match_list:
        phase = match.phase
        date = match.match_date
        if cur_date == 0:
            cur_date = date
        if cur_phase == "":
            cur_phase = phase

        if cur_phase == phase:
            if cur_date == date:
                matches.append(match)
            else:
                dates.append((cur_date, matches))
                cur_date = date
                matches = [match]
        else:
            dates.append((cur_date, matches))
            cur_date = date
            phases.append((cur_phase, dates))
            cur_phase = phase
            dates = []
            matches = [match]

    dates.append((cur_date, matches))
    phases.append((cur_phase, dates))

    return phases


def register(request):
    if request.method == 'POST':
        form = AccountCreationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            username_already_exists = False
            created = False
            user = User.objects.filter(username=username)
            if user:
                username_already_exists = True
                created = False
            else:
                user = User.objects.create_user(username, email, password)
                created = True

    else: # GET
        form = AccountCreationForm()

    return render(request, 'pronos/register.html', locals())


def connexion(request):
    error = False

    if request.method == 'POST':
        form = AccountLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user and user.is_active:
                login(request, user)
            else:
                error = True
    else:
        form = AccountLoginForm()

    return render(request, 'pronos/login.html', locals())


def deconnexion(request):
    logout(request)
    return redirect('pronos:index')


@login_required
def pronosEdit(request, cup_id):
    user = request.user
    cup_name = Cups.objects.get(pk=cup_id)
    context = {}

    if request.method == 'POST':
        PronosticFormSet = formset_factory(PronosticForm)
        formset = PronosticFormSet(request.POST)

        if formset.is_valid():
            for form in formset:
                prono_id = form.cleaned_data['prono']
                match_id = form.cleaned_data['match']
                score_a = form.cleaned_data['score_a']
                score_b = form.cleaned_data['score_b']
                winner = form.cleaned_data['winner']
                match = Matches.objects.get(pk=int(match_id))
                if not prono_id: # New prono to create
                    Pronostics.objects.create(
                        user=user,
                        match=match,
                        score_a=score_a,
                        score_b=score_b,
                        tab_winner=winner
                    )
                else: # Existing prono to modify
                    prono = Pronostics.objects.get(pk=prono_id)
                    prono.score_a = score_a
                    prono.score_b = score_b
                    prono.tab_winner = winner
                    prono.save()

            context = {
                'cup_id': cup_id,
                'cup_name': cup_name,
                'created': True,
            }
        else:
            context = createPronosticForm(cup_id, cup_name, user, formset)
            context['error'] = True
        
    else: # GET
        context = createPronosticForm(cup_id, cup_name, user)

    return render(request, 'pronos/pronostics_edit.html', context)


def createPronosticForm(cup_id, cup_name, user, previous_formset=None):
    no_available_prono = False
    match_list = Matches.objects.filter(
        cup=cup_id,
        match_date__gt=datetime.date.today()
    ).order_by('match_date')
    if not match_list:
        no_available_prono = True

    PronosticFormSet = formset_factory(PronosticForm, extra=len(match_list))
    formset = PronosticFormSet()
    i = 0
    for match in match_list:
        form = formset[i]
        # We write in the form the id of the match linked to this prono
        form.initial = {'match': match.id}
        pronos = Pronostics.objects.filter(user=user, match=match)
        winner_initial = (
            ('a', match.team_a),
            ('b', match.team_b)
        )
        # If the prono already exists for this match and this user
        if pronos and len(pronos) > 0:
            form.initial['prono'] = pronos[0].id
            form.initial['score_a'] = pronos[0].score_a
            form.initial['score_b'] = pronos[0].score_b
            if pronos[0].tab_winner == 'b':
                winner_initial = (
                    ('b', match.team_b),
                    ('a', match.team_a),
                )
        # If errors occured in previous form, set again last user values
        if previous_formset:
            if 'score_a' in previous_formset[i].cleaned_data.keys():
                form.initial['score_a'] = previous_formset[i].cleaned_data['score_a']
            if 'score_b' in previous_formset[i].cleaned_data.keys():
                form.initial['score_b'] = previous_formset[i].cleaned_data['score_b']
            if 'winner' in previous_formset[i].cleaned_data.keys():
                if previous_formset[i].cleaned_data['winner'] == 'b':
                    winner_initial = (
                        ('b', match.team_b),
                        ('a', match.team_a),
                    )

        form.fields['score_a'].label = match.team_a
        form.fields['score_b'].label = match.team_b
        form.fields['winner'].widget.choices = winner_initial
        i += 1

    return {
        'cup_id': cup_id,
        'cup_name': cup_name,
        'no_available_prono': no_available_prono,
        'formset': formset,
        'error': False,
    }


def pronostics(request, cup_id):
    cup_name = Cups.objects.get(pk=cup_id)
    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
    }

    user_list = []
    match_list = []
    matches = Matches.objects.filter(
        cup=cup_id,
        match_date__lt=datetime.date.today()
    ).order_by('match_date')
    pronos = Pronostics.objects.filter(match__cup=cup_id).order_by('user')

    # user_list filling
    i = 0
    for prono in pronos:
        if len(user_list) == 0 or user_list[-1]['name'] != prono.user.username:
            user_list.append(
                {
                    'name': prono.user.username,
                    'color': U_COLORS['dark'][i]
                }
            )
            i += 1

    # match_list filling
    color_type = 'light'
    for match in matches:
        match_pronos = pronos.filter(match=match)
        pronos_a_list = []
        pronos_b_list = []
        i = 0
        for prono in match_pronos:
            # Normally, there is one prono by user, but if one user missed a prono,
            # we have to create an empty prono for this user
            while prono.user.username != user_list[i]['name']:
                pronos_a_list.append({
                    'score': '?', 'win': '?', 'points': 0, 'color': U_COLORS[color_type][i]})
                pronos_b_list.append({
                    'score': '?', 'win': '?', 'color': U_COLORS[color_type][i]})
                i += 1

            win_val_a = 'x'
            win_val_b = ''
            if prono.tab_winner == 'b':
                win_val_a = ''
                win_val_b = 'x'
            pronos_a_list.append({
                'score': prono.score_a,
                'win': win_val_a,
                'points': prono.getScore(),
                'color': U_COLORS[color_type][i]
            })
            pronos_b_list.append({
                'score': prono.score_b, 'win': win_val_b, 'color': U_COLORS[color_type][i]
            })
            i += 1

        match_winner = match.getWinnerTeam()
        win_val_a = ''
        win_val_b = ''
        if match_winner == 'a':
            win_val_a = 'x'
            win_val_b = ''
        elif match_winner == 'b':
            win_val_a = ''
            win_val_b = 'x'
        match_list.append(
            {
                'date': match.match_date,
                'team_a': match.team_a.team_name,
                'team_b': match.team_b.team_name,
                'score_a': match.score_a,
                'score_b': match.score_b,
                'win_a': win_val_a,
                'win_b': win_val_b,
                'pronos_a': pronos_a_list,
                'pronos_b': pronos_b_list,
                'color': GREY[color_type],
            }
        )
        if color_type == 'dark':
            color_type = 'light'
        else:
            color_type = 'dark'

    context['user_list'] = user_list
    # Used to align columns of the fixed titles line with others
    context['nb_cols'] = len(user_list) * 3 + 3 
    context['match_list'] = match_list

    return render(request, 'pronos/pronostics.html', context)


def rankings(request, cup_id):
    cup_name = Cups.objects.get(pk=cup_id)
    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
    }

    (general_rank_list,
        good_1N2_rank_list,
        good_score_rank_list) = getRankingsLists(cup_id, None)
    (groups_rank_list,
        groups_good_1N2_rank_list,
        groups_good_score_rank_list) = getRankingsLists(cup_id, 'Phase de poules')
    (final_rank_list,
        final_good_1N2_rank_list,
        final_good_score_rank_list) = getRankingsLists(cup_id, 'Phase de poules', filter='exclude')

    context['general_rank_list'] = general_rank_list
    context['good_1N2_rank_list'] = good_1N2_rank_list
    context['good_score_rank_list'] = good_score_rank_list
    context['groups_rank_list'] = groups_rank_list
    context['groups_good_1N2_rank_list'] = groups_good_1N2_rank_list
    context['groups_good_score_rank_list'] = groups_good_score_rank_list
    context['final_rank_list'] = final_rank_list
    context['final_good_1N2_rank_list'] = final_good_1N2_rank_list
    context['final_good_score_rank_list'] = final_good_score_rank_list

    return render(request, 'pronos/rankings.html', context)


def getRankingsLists(cup_id, phase, filter='include'):
    general_rank_list = []
    good_1N2_rank_list = []
    good_score_rank_list = []
    pronos = None
    if not phase:
        pronos = Pronostics.objects.filter(match__cup=cup_id).order_by('user')
    elif filter == 'include':
        pronos = Pronostics.objects.filter(
            match__cup=cup_id, match__phase=phase
        ).order_by('user')
    else:
        pronos = Pronostics.objects.filter(
            match__cup=cup_id
        ).exclude(
            match__phase=phase
        ).order_by('user')

    if len(pronos) == 0:
        return (None, None, None)

    current_values = {
        'username': "",
        'score': 0,
        'nb_good_1N2': 0,
        'nb_good_2_scores': 0,
        'nb_good_1_score': 0,
        'user_nb_pronos': 0,
    }
    def initCurrentValues(current_values):
        current_values['username'] = ""
        current_values['score'] = 0
        current_values['nb_good_1N2'] = 0
        current_values['nb_good_2_scores'] = 0
        current_values['nb_good_1_score'] = 0
        current_values['user_nb_pronos'] = 0

    def incrementCurrentValues(current_values, prono):
        current_values['score'] += prono.getScore()
        if prono.isGood1N2():
            current_values['nb_good_1N2'] += 1
        if prono.is2ScoresGood():
            current_values['nb_good_2_scores'] += 1
        elif prono.is1ScoreGood():
            current_values['nb_good_1_score'] += 1

    def addUserToRankings(current_values, general_rank_list, good_1N2_rank_list, good_score_rank_list):
        general_rank_list.append((current_values['username'], current_values['score']))

        nb_pronos_percent = 100 * current_values['nb_good_1N2'] / current_values['user_nb_pronos']
        good_1N2_rank_list.append(
            (current_values['username'], current_values['nb_good_1N2'], nb_pronos_percent))

        good_score_rank_list.append(
            (current_values['username'], current_values['nb_good_2_scores'],
             current_values['nb_good_1_score']))

    for prono in pronos:
        if current_values['username'] == "":
            current_values['username'] = prono.user.username
            incrementCurrentValues(current_values, prono)
        elif current_values['username'] == prono.user.username:
            incrementCurrentValues(current_values, prono)
        else:
            addUserToRankings(current_values, general_rank_list, good_1N2_rank_list, good_score_rank_list)

            initCurrentValues(current_values)
            current_values['username'] = prono.user.username
            incrementCurrentValues(current_values, prono)

        current_values['user_nb_pronos'] += 1

    addUserToRankings(current_values, general_rank_list, good_1N2_rank_list, good_score_rank_list)

    general_rank_list.sort(key=lambda col: col[1], reverse=True)
    good_1N2_rank_list.sort(key=lambda col: col[1], reverse=True)
    good_score_rank_list.sort(key=lambda cols: cols[1]*1000+cols[2], reverse=True)

    return (general_rank_list, good_1N2_rank_list, good_score_rank_list)


def graph(request, cup_id):
    cup_name = Cups.objects.get(pk=cup_id)

    context = {
        'cup_id': cup_id,
        'cup_name': cup_name,
    }

    pronos = Pronostics.objects.filter(
        match__cup=cup_id,
        match__match_date__lt=datetime.date.today()
    ).order_by('match__match_date', 'user')

    if len(pronos) == 0:
        return render(request, 'pronos/graph.html', context)

    date_list = []
    date_index = -1
    users_scores_dict = {}

    for prono in pronos:
        match_date = str(prono.match.match_date)
        user_name = prono.user.username

        if not user_name in users_scores_dict.keys():
            users_scores_dict[user_name] = [0]

        if len(date_list) == 0 or date_list[date_index] != match_date:
            date_list.append(match_date)
            date_index += 1

        if len(users_scores_dict[user_name]) == date_index:
            users_scores_dict[user_name].append(users_scores_dict[user_name][-1])

        users_scores_dict[user_name][date_index] += prono.getScore()

    series = []
    for user_name, score_list in users_scores_dict.items():
        series.append({'name': user_name, 'data': score_list})

    chart_dict = {
        'title': {
            'text': "Graphique de l'évolution des scores des participants",
            'x': -20
        },
        'xAxis': {
            'categories': date_list
        },
        'yAxis': {
            'title': {
                'text': 'Points'
            }
        },
        'tooltip': {
            'valueSuffix': 'pts'
        },
        'legend': {
            'layout': 'vertical',
            'align': 'right',
            'verticalAlign': 'middle',
            'borderWidth': 0
        },
        'series': series
    }

    chart_js = ("$(function () {$('#container').highcharts(" +
                json.dumps(chart_dict) +
                ");});")
    context['chart_js'] = chart_js

    return render(request, 'pronos/graph.html', context)
