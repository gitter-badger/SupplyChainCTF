from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(PlayerInfo)
admin.site.register(Game)
admin.site.register(Tag)
admin.site.register(Vendor)
admin.site.register(System)
admin.site.register(SystemDependency)
admin.site.register(Event)
admin.site.register(Mitigation)

admin.site.register(GameState)
admin.site.register(SystemState)
admin.site.register(MitigationApplied)


