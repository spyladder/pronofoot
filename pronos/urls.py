from django.conf.urls import url

from . import views

app_name = 'pronos'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<cup_id>[0-9]+)/$', views.cup, name='cup'),
    url(r'^(?P<cup_id>[0-9]+)/teams/$', views.cupTeams, name='cupTeams'),
    url(r'^(?P<cup_id>[0-9]+)/teams/(?P<team_id>[0-9]+)$', views.team, name='team'),
    url(r'^(?P<cup_id>[0-9]+)/matches/$', views.matches, name='matches'),
    url(r'^(?P<cup_id>[0-9]+)/stats/$', views.stats, name='stats'),
]
