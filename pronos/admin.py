from django.contrib import admin

from .models import Cups, Matches, Teams, TeamsByCup, Pronostics

admin.site.register(Cups)
admin.site.register(Matches)
admin.site.register(Teams)
admin.site.register(TeamsByCup)
admin.site.register(Pronostics)

