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


class SeguimientoViewSet(SessionOnlyAuthMixin, viewsets.ModelViewSet):
    queryset = Seguimiento.objects.all()
    serializer_class = SeguimientoSerializer

    def get_queryset(self):
        visible_plans = Plan.objects.visible_to(self.request.user)

        return Seguimiento.objects.filter(
            accion__plan__in=visible_plans
        ).select_related(
            "accion",
            "accion__plan",
            "responsable",
        )
