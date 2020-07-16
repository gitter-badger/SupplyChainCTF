from django.contrib import admin
from django.urls import path
from .views import list_games
urlpatterns = [
    path('list/', list_games)
]
