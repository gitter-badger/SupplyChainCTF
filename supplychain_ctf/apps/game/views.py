from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Create your views here.
from .models import Game, GameState


@login_required
def list_games(request):
    games = Game.objects.all()
    return render(request, 'list_games.html', {'games': games})

@login_required
def game_state_view(request, state_id):
    state = GameState.objects.get(state_id)
    return render(request, 'game_state.html', {'game_state': state })