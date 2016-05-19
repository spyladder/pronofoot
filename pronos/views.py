from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
from django.http import Http404
from django.http import HttpResponse
from django.template import loader
from django.db.models import Q, F
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.urlresolvers import reverse
from pronos.models import *
from pronos.forms import *

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
    match_list = Matches.objects.filter(cup=cup_id)
    if not match_list:
        raise Http404("Pas de match disponible.")
    cup_name = match_list[0].cup

    nb_goals = 0
    nb_draws = 0
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

    nb_matches_total = len(match_list)
    goals_per_match = nb_goals / nb_matches_total
    draw_percent = 100 * nb_draws / nb_matches_total

    score_list_sorted = sorted(scores_dict.items(), key=lambda t: t[1], reverse=True)
    score_list_percent = []
    for score in score_list_sorted:
        score_list_percent.append((score[0], score[1], 100 * score[1] / nb_matches_total))

    match_list = Matches.objects.raw(
        ' SELECT *\
            FROM Matches\
            INNER JOIN Teams AS TA ON team_A = TA.id\
            INNER JOIN Teams AS TB ON team_B = TB.id\
            INNER JOIN Teams_by_cup AS TBCA ON team_A = TBCA.team\
            INNER JOIN Teams_by_cup AS TBCB ON team_B = TBCB.team\
            WHERE Matches.cup = %s\
                AND\
                (TBCA.fifa_rank < TBCB.fifa_rank\
                AND\
                score_A + IFNULL(score_prolong_A, 0) > score_B + IFNULL(score_prolong_B, 0)\
                OR\
                TBCA.fifa_rank > TBCB.fifa_rank\
                AND\
                score_A + IFNULL(score_prolong_A, 0) < score_B + IFNULL(score_prolong_B, 0)\
                );',
        [cup_id])
    nb_matches_won_by_favorite = 0
    for match in match_list:
        nb_matches_won_by_favorite += 1
    matches_won_by_favorite_percent = 100 * nb_matches_won_by_favorite / nb_matches_total
    matches_lost_by_favorite_percent = 100 - matches_won_by_favorite_percent - draw_percent

    context = {
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
        Q(team_a=team_id) | Q(team_b=team_id)
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
            if user:
                login(request, user)
            else:
                error = True
    else:
        form = AccountLoginForm()

    return render(request, 'pronos/login.html', locals())


def deconnexion(request):
    logout(request)
    return redirect('/pronos/')
