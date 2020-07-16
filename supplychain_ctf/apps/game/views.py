from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import render, redirect

# Create your views here.
from .models import Game, GameState, SystemState, Vendor, Event, PlayerInfo


@login_required
def list_games(request):
    player = PlayerInfo.objects.get(user=request.user)
    games = Game.objects.all()
    gamestates = GameState.objects.filter(player=player)
    return render(request, 'game/list_games.html', {'games': games, 'gamestates': gamestates })

@login_required
def start_game(request, game_id):
    game = Game.objects.get(pk=game_id)
    game_state = game.start_new_game(request.user)
    return redirect("game_state_view", game_state_id=game_state.pk)

@login_required
def game_state_view(request, game_state_id):

    # These queries looking up the current game/system state should be the largest bottleneck in the system
    # TODO: optimize it MOAR. Let's get this down to as few SQL queries as possible
    system_queryset = SystemState.objects.select_related("system")
    game_state = GameState.objects.filter(pk=game_state_id)\
        .prefetch_related(Prefetch("systemstate_set", queryset=system_queryset))

    # security check, make sure the game exists and this is a game for THIS user, not just any user
    if game_state.count() == 0 or game_state[0].player.user != request.user:
        return HttpResponseForbidden()

    this_game = game_state[0]
    all_active_tags = set(x.pk for x in this_game.all_active_tags)
    events = Event.objects.filter(game=this_game.game, at_day__gte=this_game.days_left).order_by("at_day").prefetch_related("tags")
    # add a .effected flag to the events so we can style based on whether or not it effected us
    for e in events:
        e.effected = any(t.pk in all_active_tags for t in e.tags.all())

    return render(request, 'game/game_state.html', {
        'game_state': this_game,
        'events': events,
         })

@login_required
def next_turn_view(request, game_state_id):

    game_state = GameState.objects.filter(pk=game_state_id)

    # security check, make sure the game exists and this is a game for THIS user, not just any user
    if game_state.count() == 0 or game_state[0].player.user != request.user:
        return HttpResponseForbidden()

    this_game = game_state[0]
    if not this_game.finished:
        this_game.game_tick()
        this_game.save()

    return redirect("game_state_view", game_state_id=this_game.pk)

@login_required
def procure_systemstate(request, systemstate_id, vendor_id):
    systemstate_set = SystemState.objects.filter(pk=systemstate_id).select_related("game_state__player")
    # security check, make sure the game exists and this is a game for THIS user, not just any user
    if systemstate_set.count() == 0 or systemstate_set[0].game_state.player.user != request.user:
        return HttpResponseForbidden()

    systemstate = systemstate_set[0]
    vendor = Vendor.objects.get(pk=vendor_id)
    if systemstate.procured:
        return HttpResponseForbidden("Nice try but you've already procured this one")

    if systemstate.game_state.finished:
        return HttpResponseForbidden("Nice try but this scenario is over")

    if not systemstate.all_deps_fulfilled:
        return HttpResponseForbidden("Nice try but you don't have all dependencies purchased yet")

    systemstate.procured = True
    systemstate.chosen_vendor = vendor
    # adjust and apply the costs
    systemstate.downtime += int(systemstate.system.downtime_cost*vendor.downtime_cost_multiplier)
    systemstate.game_state.score -= int(systemstate.system.setup_cost*vendor.setup_cost_multiplier)
    # adjust the tags
    tags = list(systemstate.system.tags.all())
    tags.extend(x for x in vendor.tags.all())
    print(tags)
    systemstate.active_tags.set(tags)
    # save it and return
    systemstate.save()
    systemstate.game_state.save()

    return redirect("game_state_view", game_state_id=systemstate.game_state.pk)

