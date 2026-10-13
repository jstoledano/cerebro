from django.db.models import Count

from apps.art141.models import UniversoVA


def get_universo_va():
    return UniversoVA.objects.filter(
        activo=True
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
            .exclude(manzana_origen=9999)
            .values(
                "seccion_origen",
                "localidad",
                "manzana_origen",
            )
            .distinct()
            .count()
        ),

        "con_referencia": (
            universo
            .exclude(seccion__isnull=True)
            .count()
        ),

        "georreferencia_pendiente": (
            universo
            .filter(seccion__isnull=True)
            .count()
        ),

        "nivel_manzana": (
            universo
            .exclude(manzana__isnull=True)
            .count()
        ),

        "nivel_localidad": (
            universo
            .filter(
                manzana__isnull=True,
                localidad_mge__isnull=False,
            )
            .count()
        ),

        "nivel_seccion": (
            universo
            .filter(
                manzana__isnull=True,
                localidad_mge__isnull=True,
                seccion__isnull=False,
            )
            .count()
        ),
    }


def get_va_por_distrito():
    return list(
        get_universo_va()
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
        get_universo_va()
        .exclude(seccion_origen__isnull=True)
        .values(
            "distrito",
            "seccion_origen",
            "seccion_id",
        )
        .annotate(
            personas=Count("id"),
            manzanas=Count(
                "manzana_origen",
                distinct=True,
            ),
        )
        .order_by(
            "distrito",
            "seccion_origen",
        )
    )


def get_distribucion_va_por_seccion():
    secciones = get_va_por_seccion()

    distribucion = {
        "1": 0,
        "2": 0,
        "3_5": 0,
        "6_10": 0,
        "11_mas": 0,
    }

    max_personas = 0
    seccion_max = None

    for item in secciones:
        personas = item["personas"]

        if personas > max_personas:
            max_personas = personas
            seccion_max = item["seccion_origen"]

        if personas == 1:
            distribucion["1"] += 1
        elif personas == 2:
            distribucion["2"] += 1
        elif personas <= 5:
            distribucion["3_5"] += 1
        elif personas <= 10:
            distribucion["6_10"] += 1
        else:
            distribucion["11_mas"] += 1

    return {
        "secciones": len(secciones),
        "distribucion": distribucion,
        "max_personas": max_personas,
        "seccion_max": seccion_max,
    }
