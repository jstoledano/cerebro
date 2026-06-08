import django_filters
from django.db.models import Q
from django.forms.widgets import Input
from control.models import  Seccion


class SeccionFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = Seccion
        fields = ['municipio', 'seccion']
