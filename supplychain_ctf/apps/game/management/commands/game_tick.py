from io import BytesIO
import gzip
from django.core.management.base import BaseCommand, CommandError
from urllib.parse import unquote

from django.db import transaction
from django.db.utils import IntegrityError

from supplychain_ctf.supplychain_ctf.apps.game.models import GameState


class Command(BaseCommand):
    help = 'Downloads all of the CPEs from NIST'
    # suffixes that don't mean anything and should be removed so we match the common name
    USELESS_SUFFIXES = (' on x64', ' 64-bit', " Gold")

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        queued_games = GameState.objects.filter(started=False, finished=False)
        for g in queued_games:
            g.started = True
            g.save()

        active_games = GameState.objects.filter(started=True, finished=False)
        for g in active_games:
            # finish games with days_left at 0
            if g.days_left <= 0:
                g.finished = True
                g.save()

            else:
                g.days_left -= 1

                # does an attacker exploit a vuln?
                







