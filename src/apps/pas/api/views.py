from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.pas.views import usuario_puede_gestionar_evidencia
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
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        visible_plans = Plan.objects.visible_to(
            self.request.user
        )

        return (
            Evidencia.objects
            .filter(
                ejecucion__ciclo__accion__plan__in=visible_plans,
            )
            .select_related(
                "ejecucion",
                "ejecucion__responsable",
                "ejecucion__ciclo",
                "ejecucion__ciclo__accion",
                "ejecucion__ciclo__accion__plan",
                "user",
            )
        )

    def validar_mutacion(self, execution, operacion):
        if not usuario_puede_gestionar_evidencia(
            self.request.user,
            execution,
            operacion,
        ):
            raise PermissionDenied(
                "No tienes permiso para realizar esta operación "
                "sobre las evidencias de esta ejecución."
            )

        if not execution.plan.permite_modificaciones:
            raise ValidationError(
                "El plan se encuentra cerrado "
                "o no admite modificaciones."
            )

        if execution.completada:
            raise ValidationError(
                "La ejecución está terminada. Debes reabrirla "
                "antes de modificar sus evidencias."
            )

    def perform_create(self, serializer):
        execution = serializer.validated_data["ejecucion"]
        self.validar_mutacion(execution, "crear")

        serializer.save(
            user=self.request.user,
            accion=None,
        )

    def perform_update(self, serializer):
        self.validar_mutacion(
            serializer.instance.ejecucion,
            "editar",
        )
        serializer.save()

    def perform_destroy(self, instance):
        self.validar_mutacion(
            instance.ejecucion,
            "eliminar",
        )
        instance.delete()

