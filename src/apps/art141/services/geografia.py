from django.db.models import Count

from apps.art141.models import RegistroArt141


def get_art141_por_distrito():
    return list(
        RegistroArt141.objects
        .values("distrito")
        .annotate(
            tramites=Count("id"),
            personas=Count(
                "ciudadano_id",
                distinct=True,
            ),
            secciones=Count(
                "seccion_origen",
                distinct=True,
            ),
        )
        .order_by("distrito")
    )


def get_art141_por_seccion():
    return list(
        RegistroArt141.objects
        .values(
            "distrito",
            "seccion_origen",
        )
        .annotate(
            tramites=Count("id"),
            personas=Count(
                "ciudadano_id",
                distinct=True,
            ),
        )
        .order_by(
            "distrito",
            "seccion_origen",
        )
    )


def get_georreferencia_art141():
    queryset = RegistroArt141.objects.all()

    georreferencia_valida = (
        queryset
        .exclude(seccion__isnull=True)
        .count()
    )

    georreferencia_pendiente = (
        queryset
        .filter(seccion__isnull=True)
        .count()
    )

    sin_referencia_manzana = (
        queryset
        .exclude(seccion__isnull=True)
        .filter(manzana__isnull=True)
        .count()
    )

    return {
        "georreferencia_valida": georreferencia_valida,
        "georreferencia_pendiente": georreferencia_pendiente,
        "sin_referencia_manzana": sin_referencia_manzana,
    }
