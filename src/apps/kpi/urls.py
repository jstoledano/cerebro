from django.urls import path
from .views import KpiIndex

app_name = 'kpi'

urlpatterns = [
    path('', KpiIndex.as_view(), name='index'),
]
