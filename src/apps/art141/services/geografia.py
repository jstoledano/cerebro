from django.db.models import Count

from apps.art141.models import TramiteArt141, UniversoVA


def get_art141_por_distrito():
    return list(
        TramiteArt141.objects
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
        TramiteArt141.objects
        .exclude(seccion_origen__isnull=True)
        .values(
            "distrito",
            "seccion_origen",
            "seccion_id",
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


def get_va_por_distrito():
    return list(
        UniversoVA.objects
        .filter(activo=True)
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


def get_va_por_seccion():
    return list(
        UniversoVA.objects
        .filter(activo=True)
        .exclude(seccion_origen__isnull=True)
        .values(
            "distrito",
            "seccion_origen",
            "seccion_id",
        )
        .annotate(
            personas=Count("id"),
        )
        .order_by(
            "distrito",
            "seccion_origen",
        )
    )


def get_georreferencia_art141():
    return _get_niveles_georreferencia(
        TramiteArt141.objects.all()
    )


def get_georreferencia_va():
    return _get_niveles_georreferencia(
        UniversoVA.objects.filter(
            activo=True
        )
    )


def _get_niveles_georreferencia(queryset):
    nivel_manzana = queryset.filter(
        manzana__isnull=False
    ).count()

    nivel_localidad = queryset.filter(
        manzana__isnull=True,
        localidad_mge__isnull=False,
    ).count()

    nivel_seccion = queryset.filter(
        manzana__isnull=True,
        localidad_mge__isnull=True,
        seccion__isnull=False,
    ).count()

    pendiente = queryset.filter(
        seccion__isnull=True
    ).count()

    total = queryset.count()

    con_referencia = (
        nivel_manzana
        + nivel_localidad
        + nivel_seccion
    )

    return {
        "total": total,
        "con_referencia": con_referencia,
        "nivel_manzana": nivel_manzana,
        "nivel_localidad": nivel_localidad,
        "nivel_seccion": nivel_seccion,
        "georreferencia_pendiente": pendiente,
    }
