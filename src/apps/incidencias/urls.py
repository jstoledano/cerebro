# coding: utf-8
#         app: incidencias
#      module: urls.py
#        date: miércoles, 06 de junio de 2018 - 11:30
# description: Patrones de ruta de cobertura.
# pylint: disable=W0613,R0201,R0903


from django.urls import path
from apps.incidencias.views import Portada, EventoDetail

app_name = 'incidencias'
urlpatterns = [
    path('', Portada.as_view(), name='index'),
    path('<int:pk>/', EventoDetail.as_view(), name='evento')
]
