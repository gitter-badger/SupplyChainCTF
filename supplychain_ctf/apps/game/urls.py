from django.contrib import admin
from django.urls import path
from .views import list_games, home, start_game, game_state_view, procure_systemstate

urlpatterns = [
    path('list/', list_games),
    path('start_game/<int:game_id>/', start_game, name='start_game_view'),
    path('game_state/<int:game_state_id>/', game_state_view, name='game_state_view'),
    path('procure_systemstate/<int:systemstate_id>/<int:vendor_id>', procure_systemstate, name='procure_systemstate'),
    path('', list_games)
]
