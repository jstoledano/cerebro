from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import DjangoModelPermissions

from apps.pas.models import Plan, Accion, Seguimiento
from .serializers import PlanSerializer, AccionSerializer, SeguimientoSerializer


class SessionOnlyAuthMixin:
    authentication_classes = (SessionAuthentication,)
    permission_classes = (DjangoModelPermissions,)


class PlanViewSet(SessionOnlyAuthMixin, viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer


class AccionViewSet(SessionOnlyAuthMixin, viewsets.ModelViewSet):
    queryset = Accion.objects.all()
    serializer_class = AccionSerializer


class SeguimientoViewSet(SessionOnlyAuthMixin, viewsets.ModelViewSet):
    queryset = Seguimiento.objects.all()
    serializer_class = SeguimientoSerializer
