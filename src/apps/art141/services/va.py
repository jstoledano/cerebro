from django.db.models import Count, F, Window
from django.db.models.functions import RowNumber

from apps.art141.models import RegistroArt141


def get_universo_va():
    """
    Devuelve una sola fila por persona para el universo preliminar
    de Voto Anticipado.

    Reglas:
    - ESTATUSCIUDADANO_ID = 2
    - 1 CIUDADANO_ID = 1 persona
    - Si existen varios registros de la misma persona, se conserva
      el de fecha de entrega de credencial más reciente.
    """

    return (
        RegistroArt141.objects
        .filter(estatusciudadano_id=2)
        .annotate(
            orden_va=Window(
                expression=RowNumber(),
                partition_by=[
                    F("ciudadano_id"),
                ],
                order_by=[
                    F("fecha_entrega_credencial").desc(
                        nulls_last=True
                    ),
                    F("fecha_solicitud_tramite").desc(
                        nulls_last=True
                    ),
                    F("id").desc(),
                ],
            )
        )
        .filter(orden_va=1)
    )


def get_resumen_va():
    universo = get_universo_va()

    return {
        "personas": universo.count(),

        "distritos": (
            universo
            .exclude(distrito__isnull=True)
            .values("distrito")
            .distinct()
            .count()
        ),

        "municipios": (
            universo
            .exclude(municipio="")
            .values("municipio")
            .distinct()
            .count()
        ),

        "secciones": (
            universo
            .exclude(seccion_origen__isnull=True)
            .values("seccion_origen")
            .distinct()
            .count()
        ),

        "localidades": (
            universo
            .exclude(localidad__isnull=True)
            .values(
                "seccion_origen",
                "localidad",
            )
            .distinct()
            .count()
        ),

        "manzanas": (
            universo
            .exclude(manzana_origen__isnull=True)
            .values(
                "seccion_origen",
                "localidad",
                "manzana_origen",
            )
            .distinct()
            .count()
        ),

        "georreferencia_valida": (
            universo
            .exclude(seccion__isnull=True)
            .count()
        ),

        "georreferencia_pendiente": (
            universo
            .filter(seccion__isnull=True)
            .count()
        ),

        "sin_referencia_manzana": (
            universo
            .exclude(seccion__isnull=True)
            .filter(manzana__isnull=True)
            .count()
        ),
    }


def get_va_por_distrito():
    universo = get_universo_va()

    return list(
        universo
        .values("distrito")
        .annotate(
            personas=Count("id"),
            secciones=Count(
                "seccion_origen",
                distinct=True,
            ),
        )
        .order_by("distrito")
    )
