from rest_framework import viewsets
from django.db.models import Q
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import DjangoModelPermissions

from apps.pas.models import (
    Plan,
    Accion,
    Evidencia,
)
from .serializers import (
    PlanSerializer,
    AccionSerializer,
    EvidenciaSerializer,
)

class SessionOnlyAuthMixin:
    authentication_classes = (SessionAuthentication,)
    permission_classes = (DjangoModelPermissions,)


class PlanViewSet(SessionOnlyAuthMixin, viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def get_queryset(self):
        return Plan.objects.visible_to(self.request.user)


class AccionViewSet(SessionOnlyAuthMixin, viewsets.ModelViewSet):
    queryset = Accion.objects.all()
    serializer_class = AccionSerializer

    def get_queryset(self):
        visible_plans = Plan.objects.visible_to(self.request.user)

        return (
            Accion.objects
            .filter(plan__in=visible_plans)
            .select_related("plan", "responsable")
        )


class EvidenciaViewSet(
    SessionOnlyAuthMixin,
    viewsets.ModelViewSet,
):
    queryset = Evidencia.objects.all()
    serializer_class = EvidenciaSerializer

    def get_queryset(self):
        visible_plans = (
            Plan.objects.visible_to(
                self.request.user
            )
        )

        return (
            Evidencia.objects
            .filter(
                Q(
                    ejecucion__ciclo__accion__plan__in=(
                        visible_plans
                    )
                )
                |
                Q(
                    accion__plan__in=(
                        visible_plans
                    )
                )
            )
            .select_related(
                "ejecucion",
                "ejecucion__ciclo",
                "ejecucion__ciclo__accion",
                "ejecucion__ciclo__accion__plan",
                "accion",
                "accion__plan",
                "user",
            )
            .distinct()
        )
