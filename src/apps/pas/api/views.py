from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.pas.permissions import (
    usuario_puede_gestionar_evidencia, ejecuciones_gestionables, es_normativo_ejecucion,
)
from apps.pas.evidence_services import guardar_evidencia, eliminar_evidencia
from apps.pas.filters import EvidenciaFilterForm, filtrar_evidencias
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

        queryset = (
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

        if self.action in {"list", "retrieve"}:
            queryset = queryset.filter(ejecucion__in=ejecuciones_gestionables(self.request.user))
        if self.action == "list":
            form = EvidenciaFilterForm(self.request.query_params)
            if not form.is_valid():
                raise ValidationError(form.errors)
            queryset = filtrar_evidencias(queryset, form.cleaned_data)
        return queryset

    def get_object(self):
        evidence = super().get_object()
        operacion = {"update": "editar", "partial_update": "editar", "destroy": "eliminar"}.get(self.action)
        if operacion and not usuario_puede_gestionar_evidencia(self.request.user, evidence.ejecucion, operacion):
            raise PermissionDenied("La evidencia está fuera de tu ámbito de supervisión.")
        return evidence

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

        if execution.completada and not (
            operacion == "editar" and es_normativo_ejecucion(self.request.user, execution)
        ):
            raise ValidationError(
                "La ejecución está terminada. Debes reabrirla "
                "antes de modificar sus evidencias."
            )

    def perform_create(self, serializer):
        execution = serializer.validated_data["ejecucion"]
        self.validar_mutacion(execution, "crear")

        serializer.instance = guardar_evidencia(
            Evidencia(**serializer.validated_data, accion=None), self.request.user,
        )

    def perform_update(self, serializer):
        self.validar_mutacion(
            serializer.instance.ejecucion,
            "editar",
        )
        for name, value in serializer.validated_data.items():
            setattr(serializer.instance, name, value)
        serializer.instance = guardar_evidencia(serializer.instance, self.request.user)

    def perform_destroy(self, instance):
        self.validar_mutacion(
            instance.ejecucion,
            "eliminar",
        )
        eliminar_evidencia(instance, self.request.user)


