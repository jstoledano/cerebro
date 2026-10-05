from django.db.models import Avg, Count, ExpressionWrapper, F, fields
from django.db.models.functions import ExtractDay

from apps.art141.models import RegistroArt141


def get_resumen_art141():
    queryset = RegistroArt141.objects.all()

    tramites = queryset.count()

    personas = (
        queryset
        .values("ciudadano_id")
        .distinct()
        .count()
    )

    credenciales_entregadas = (
        queryset
        .exclude(fecha_entrega_credencial__isnull=True)
        .count()
    )

    sin_fecha_entrega = (
        queryset
        .filter(fecha_entrega_credencial__isnull=True)
        .count()
    )

    personas_lista_nominal = (
        queryset
        .filter(estatusciudadano_id=2)
        .values("ciudadano_id")
        .distinct()
        .count()
    )

    return {
        "tramites": tramites,
        "personas": personas,
        "credenciales_entregadas": credenciales_entregadas,
        "sin_fecha_entrega": sin_fecha_entrega,
        "personas_lista_nominal": personas_lista_nominal,
    }


def get_tramites_por_anio():
    return list(
        RegistroArt141.objects
        .exclude(fecha_solicitud_tramite__isnull=True)
        .values("fecha_solicitud_tramite__year")
        .annotate(tramites=Count("id"))
        .order_by("fecha_solicitud_tramite__year")
    )


def get_tiempos_entrega():
    queryset = (
        RegistroArt141.objects
        .exclude(fecha_solicitud_tramite__isnull=True)
        .exclude(fecha_entrega_credencial__isnull=True)
    )

    duracion = ExpressionWrapper(
        F("fecha_entrega_credencial")
        - F("fecha_solicitud_tramite"),
        output_field=fields.DurationField(),
    )

    registros = queryset.annotate(
        duracion=duracion
    ).values(
        "id",
        "ciudadano_id",
        "fecha_solicitud_tramite",
        "fecha_entrega_credencial",
        "distrito",
        "seccion_origen",
        "duracion",
    )

    resultados = []

    for registro in registros:
        duracion = registro["duracion"]

        if duracion is None:
            continue

        resultados.append(
            {
                "id": registro["id"],
                "ciudadano_id": registro["ciudadano_id"],
                "fecha_solicitud": registro[
                    "fecha_solicitud_tramite"
                ],
                "fecha_entrega": registro[
                    "fecha_entrega_credencial"
                ],
                "distrito": registro["distrito"],
                "seccion": registro["seccion_origen"],
                "dias": duracion.days,
            }
        )

    return resultados
