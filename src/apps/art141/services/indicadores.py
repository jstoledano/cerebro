from django.db.models import Count, ExpressionWrapper, F, fields

from apps.art141.models import TramiteArt141


def get_resumen_art141():
    queryset = TramiteArt141.objects.all()

    return {
        "tramites": queryset.count(),

        "personas": (
            queryset
            .values("ciudadano_id")
            .distinct()
            .count()
        ),

        "credenciales_entregadas": (
            queryset
            .exclude(fecha_entrega_credencial__isnull=True)
            .count()
        ),

        "sin_fecha_entrega": (
            queryset
            .filter(fecha_entrega_credencial__isnull=True)
            .count()
        ),
    }


def get_tramites_por_anio():
    return list(
        TramiteArt141.objects
        .exclude(fecha_solicitud_tramite__isnull=True)
        .values("fecha_solicitud_tramite__year")
        .annotate(
            tramites=Count("id"),
        )
        .order_by("fecha_solicitud_tramite__year")
    )


def get_tiempos_entrega():
    queryset = (
        TramiteArt141.objects
        .exclude(fecha_solicitud_tramite__isnull=True)
        .exclude(fecha_entrega_credencial__isnull=True)
    )

    duracion = ExpressionWrapper(
        F("fecha_entrega_credencial")
        - F("fecha_solicitud_tramite"),
        output_field=fields.DurationField(),
    )

    registros = (
        queryset
        .annotate(duracion=duracion)
        .values(
            "id",
            "ciudadano_id",
            "fecha_solicitud_tramite",
            "fecha_entrega_credencial",
            "distrito",
            "seccion_origen",
            "seccion_id",
            "duracion",
        )
        .order_by(
            "fecha_solicitud_tramite",
            "id",
        )
    )

    resultados = []

    for registro in registros:
        duracion_registro = registro["duracion"]

        if duracion_registro is None:
            continue

        resultados.append(
            {
                "id": registro["id"],
                "ciudadano_id": registro["ciudadano_id"],
                "fecha_solicitud": (
                    registro["fecha_solicitud_tramite"]
                ),
                "fecha_entrega": (
                    registro["fecha_entrega_credencial"]
                ),
                "distrito": registro["distrito"],
                "seccion_origen": registro["seccion_origen"],
                "seccion_id": registro["seccion_id"],
                "dias": duracion_registro.days,
            }
        )

    return resultados
