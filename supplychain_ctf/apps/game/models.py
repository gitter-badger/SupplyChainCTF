from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
# -1 is used throughout the models with unisigned ints to signify that it should be considered default/invalid
from django.db.models.signals import post_save
from django.dispatch import receiver

INVALID_UINT = -1
MAX_TAG_LENGTH = 64


class PlayerInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.user)


@receiver(post_save, sender=User)
def create_player(sender, instance, created, **kwargs):
    if created:
        info = PlayerInfo(user=instance)
        info.save()


# META INFORMATION
class Game(models.Model):
    name = models.CharField(max_length=64)
    total_days = models.IntegerField(default=1, help_text="The total number of days that the game takes place")
    systems = models.ManyToManyField("System")

    def start_new_game(self, user):
        """
        Logic to start a new game
        :param user:
        :return:
        """

        # create the game state for this instance of the game
        game_state = GameState(game=self, player=user, days_left=self.total_days)
        game_state.save()

        # create the system state for every system in the game state
        system_states = []
        for system in self.systems.all():
            system_states.append(SystemState(system=system, game_state=game_state))

        SystemState.objects.bulk_create(system_states)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """
    A text-based tag. This is added to make foreign keys and queries easier
    """
    tag_name = models.CharField(max_length=MAX_TAG_LENGTH, primary_key=True)
    visible = models.BooleanField(default=True, help_text="Should the user be able to see this tag?")


class Vendor(models.Model):
    """
    A Vendor for a system
    """
    name = models.CharField(max_length=64)
    tags = models.ManyToManyField(Tag)


class System(models.Model):
    """
    A type of system
    """
    name = models.CharField(max_length=64)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    score_per_day = models.IntegerField(default=0, help_text="Amount of score this will generate per day if active")
    tags = models.ManyToManyField(Tag)

    def __str__(self):
        return self.name


class SystemDependency(models.Model):
    """
    When a parent system requires a different system type (uses tags to meet deps)
    """
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    child_tag = models.ForeignKey(Tag, on_delete=models.CASCADE,
                                  help_text="In order to purchase this system you must have this tag")


class Event(models.Model):
    """
    An event happens during the game. Could be good, or bad
    """
    name = models.CharField(max_length=64)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag)
    at_day = models.IntegerField(help_text="happens at this many days left")

    # What happens to systems with this tag?
    downtime = models.IntegerField(default=0, help_text="Downtime caused by this event")
    score = models.IntegerField(default=0,
                                help_text="Cost of this event. Positive means gain in score, negative means drop in score")

    def __str__(self):
        return f"{self.game}-{self.name}-{self.at_day}"


class Mitigation(models.Model):
    """
    A mitigation for a system
    """
    mitigation_name = models.CharField(max_length=20)
    system = models.ForeignKey(System, on_delete=models.CASCADE)

    adds_tags = models.ManyToManyField(Tag, help_text="The mitigation adds the following tags")
    removes_tags = models.ManyToManyField(Tag, help_text="The mitigation removes the following tags")

    cost = models.IntegerField(default=1, help_text="The cost to apply this mitigation")
    downtime_days = models.IntegerField(default=1, help_text="The amount of downtime to apply")

    def __str__(self):
        return f"{self.mitigation_name} {self.system}"


# GAME STATE INFORMATION
class GameState(models.Model):
    """
    The state of a single game for a single Player/User
    """
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    player = models.ForeignKey(PlayerInfo, on_delete=models.CASCADE)
    days_left = models.IntegerField(default=0, help_text="Number of game days left. "
                                                         "This is the global time for the entire game state"
                                                         "All time in state objects is defined in number of days left"
                                                         "(e.g. a lower number is AFTER a higher number)")
    score = models.IntegerField(default=0, help_text="The score for this game")
    started = models.BooleanField(default=False, help_text="Has the game started yet?")
    finished = models.BooleanField(default=False, help_text="Is the game finished?")

    def game_tick(self):
        """
        Process logic for this gamestate when a day passes
        returns a querset of events that occured today
        :return:
        """

        # if we haven't started yet, then start the game and eject
        if not self.started:
            self.started = True
            return

        # Are we finished with the game ?
        if self.days_left <= 0:
            self.finished = True
            return

        # Game is active, so do logic
        # days go down by one
        self.days_left -= 1

        # Any events on this day?
        events = Event.objects.filter(game=self.game, at_day=self.days_left)
        procured_systems = self.systemstate_set.filter(procured=True).select_related("active_tags")

        # process the events
        for event in events:
            event_tags = set(event.tags.all())
            # find any procured systems with the tags that trigger this event
            # TODO This could definitely be optimized into a single query
            for ps in procured_systems:
                # if there is ANY intersectionality in these sets, then do the event effects
                if len(set(ps.active_tags.all()).intersection(event_tags)) > 0:
                    ps.downtime += event.downtime
                    self.score += event.score
                    ps.save()

        self.save()
        return events

    def __str__(self):
        return str(self.game) + " " + str(self.pk)


class SystemState(models.Model):
    """
    An instance of a single system within a game
    """
    game_state = models.ForeignKey(GameState, on_delete=models.CASCADE)
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    procured = models.BooleanField(default=False)
    downtime = models.IntegerField(default=0, help_text="How many days of downtime left? if this value is <= 0 " +
                                                        "it means the system is operational")

    active_tags = models.ManyToManyField(Tag)

    def __str__(self):
        return self.pk + str(self.game_state) + str(self.system)


class MitigationApplied(models.Model):
    """
    Represents a user applying a patch to a system
    """
    mitigation = models.ForeignKey(Mitigation, on_delete=models.CASCADE)
    applied_on = models.IntegerField(default=INVALID_UINT, help_text="How many days were left when this was applied")