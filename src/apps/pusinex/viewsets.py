from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from .models import Entidad, Distrito, Municipio, Pusinex, Seccion
from .serializers import (
    EntidadSerializer,
    DistritoSerializer,
    MunicipioSerializer,
    PusinexSerializer,
    SeccionSerializer,
)


class EntidadViewSet(viewsets.ModelViewSet):
    queryset = Entidad.objects.all()
    serializer_class = EntidadSerializer


class DistritoViewSet(viewsets.ModelViewSet):
    queryset = Distrito.objects.all()
    serializer_class = DistritoSerializer


class MunicipioViewSet(viewsets.ModelViewSet):
    queryset = Municipio.objects.all()
    serializer_class = MunicipioSerializer


class PusinexViewSet(viewsets.ModelViewSet):
    queryset = Pusinex.objects.all()
    serializer_class = PusinexSerializer
    filterset_fields = ['id', 'seccion__seccion', ]


class SeccionViewSet(viewsets.ModelViewSet):
    queryset = Seccion.objects.filter(activa=True).order_by('distrito', 'municipio', 'seccion')
    serializer_class = SeccionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['municipio', 'seccion']
