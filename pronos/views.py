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
    yesterday = datetime.date.today() - datetime.timedelta(1)
    match_list = Matches.objects.filter(
        cup=cup_id,
        match_date__lte=yesterday
    )
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

    yesterday = datetime.date.today() - datetime.timedelta(1)
    match_list = Matches.objects.filter(
        Q(cup=cup_id),
        Q(team_a=team_id) | Q(team_b=team_id),
        Q(match_date__lte=yesterday)
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
        # TODO gérer les erreurs
        print(formset.errors)
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
            context = createPronosticForm(cup_id, cup_name, user)
        
    else: # GET
        context = createPronosticForm(cup_id, cup_name, user)

    return render(request, 'pronos/pronostics_edit.html', context)


def createPronosticForm(cup_id, cup_name, user):
    no_available_prono = False
    tomorrow = datetime.date.today() + datetime.timedelta(1)
    match_list = Matches.objects.filter(
        cup=cup_id,
        match_date__gte=tomorrow
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


        form.fields['score_a'].label = match.team_a
        form.fields['score_b'].label = match.team_b
        form.fields['winner'].widget.choices = winner_initial
        i += 1

    return {
        'cup_id': cup_id,
        'cup_name': cup_name,
        'no_available_prono': no_available_prono,
        'formset': formset,
    }
