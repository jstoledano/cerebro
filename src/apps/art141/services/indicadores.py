from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear

from apps.art141.models import TramiteArt141


MESES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def _queryset(anio=None):
    qs = TramiteArt141.objects.all()

    if anio:
        qs = qs.filter(
            fecha_solicitud_tramite__year=anio
        )

    return qs


def get_resumen_art141(anio=None):
    tramites = _queryset(anio)

    personas = (
        tramites
        .values("ciudadano_id")
        .distinct()
        .count()
    )

    personas_recurrentes = (
        tramites
        .values("ciudadano_id")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
        .count()
    )

    return {
        "tramites": tramites.count(),
        "personas": personas,
        "secciones": (
            tramites
            .exclude(seccion_origen__isnull=True)
            .values("seccion_origen")
            .distinct()
            .count()
        ),
        "personas_recurrentes": personas_recurrentes,
    }


def get_anios_disponibles():
    return list(
        TramiteArt141.objects
        .exclude(fecha_solicitud_tramite__isnull=True)
        .annotate(
            anio=ExtractYear(
                "fecha_solicitud_tramite"
            )
        )
        .values_list("anio", flat=True)
        .distinct()
        .order_by("-anio")
    )


def get_tramites_por_mes(anio=None):
    qs = (
        _queryset(anio)
        .exclude(fecha_solicitud_tramite__isnull=True)
    )

    datos = (
        qs
        .annotate(
            mes=ExtractMonth(
                "fecha_solicitud_tramite"
            )
        )
        .values("mes")
        .annotate(
            tramites=Count("id"),
            personas=Count(
                "ciudadano_id",
                distinct=True,
            ),
        )
        .order_by("mes")
    )

    por_mes = {
        item["mes"]: item
        for item in datos
    }

    return [
        {
            "mes": numero,
            "nombre": MESES[numero - 1],
            "tramites": por_mes.get(
                numero,
                {},
            ).get("tramites", 0),
            "personas": por_mes.get(
                numero,
                {},
            ).get("personas", 0),
        }
        for numero in range(1, 13)
    ]


def get_distribucion_sexo(anio=None):
    qs = _queryset(anio)

    resultado = {
        "hombres": 0,
        "mujeres": 0,
        "sin_dato": 0,
    }

    for item in (
        qs
        .values("sexo")
        .annotate(total=Count("id"))
    ):
        sexo = (
            item["sexo"]
            or ""
        ).strip().upper()

        total = item["total"]

        if sexo in {
            "H",
            "HOMBRE",
            "MASCULINO",
        }:
            resultado["hombres"] += total

        elif sexo in {
            "M",
            "MUJER",
            "F",
            "FEMENINO",
        }:
            resultado["mujeres"] += total

        else:
            resultado["sin_dato"] += total

    resultado["total"] = (
        resultado["hombres"]
        + resultado["mujeres"]
        + resultado["sin_dato"]
    )

    return resultado


def get_piramide_edades(anio=None):
    qs = (
        _queryset(anio)
        .exclude(edad__isnull=True)
    )

    grupos = [
        (18, 24),
        (25, 34),
        (35, 44),
        (45, 54),
        (55, 64),
        (65, 74),
        (75, 84),
        (85, 94),
        (95, None),
    ]

    resultado = []

    for minimo, maximo in grupos:
        base = qs.filter(
            edad__gte=minimo
        )

        if maximo is not None:
            base = base.filter(
                edad__lte=maximo
            )

        hombres = base.filter(
            sexo__in=[
                "H",
                "HOMBRE",
                "MASCULINO",
            ]
        ).count()

        mujeres = base.filter(
            sexo__in=[
                "M",
                "MUJER",
                "F",
                "FEMENINO",
            ]
        ).count()

        etiqueta = (
            f"{minimo}-{maximo}"
            if maximo is not None
            else f"{minimo}+"
        )

        resultado.append(
            {
                "grupo": etiqueta,
                "hombres": hombres,
                "mujeres": mujeres,
            }
        )

    return resultado


def get_sankey_distritos(anio=None):
    qs = _queryset(anio)

    distritos = list(
        qs
        .exclude(distrito__isnull=True)
        .values("distrito")
        .annotate(
            tramites=Count("id"),
            secciones=Count(
                "seccion_origen",
                distinct=True,
            ),
        )
        .order_by("distrito")
    )

    secciones = list(
        qs
        .exclude(distrito__isnull=True)
        .exclude(seccion_origen__isnull=True)
        .values(
            "distrito",
            "seccion_origen",
        )
        .annotate(
            tramites=Count("id")
        )
        .order_by(
            "distrito",
            "seccion_origen",
        )
    )

    return {
        "total": qs.count(),
        "distritos": distritos,
        "secciones": secciones,
    }


def get_desempeno_afectacion(anio=None):
    qs = (
        _queryset(anio)
        .exclude(fecha_solicitud_tramite__isnull=True)
        .exclude(fecha_afectacion_padron__isnull=True)
    )

    valores = []

    for tramite in qs.only(
        "fecha_solicitud_tramite",
        "fecha_afectacion_padron",
    ):
        dias = (
            tramite.fecha_afectacion_padron
            - tramite.fecha_solicitud_tramite
        ).days

        if dias >= 0:
            valores.append(dias)

    valores.sort()

    if not valores:
        return {
            "casos": 0,
            "mediana": None,
            "p75": None,
            "p90": None,
            "minimo": None,
            "maximo": None,
        }

    return {
        "casos": len(valores),
        "mediana": _percentil(
            valores,
            50,
        ),
        "p75": _percentil(
            valores,
            75,
        ),
        "p90": _percentil(
            valores,
            90,
        ),
        "minimo": valores[0],
        "maximo": valores[-1],
    }


def get_distribucion_dias_afectacion(anio=None):
    qs = (
        _queryset(anio)
        .exclude(fecha_solicitud_tramite__isnull=True)
        .exclude(fecha_afectacion_padron__isnull=True)
    )

    rangos = {
        "0-1": 0,
        "2-3": 0,
        "4-7": 0,
        "8-15": 0,
        "16-30": 0,
        "31+": 0,
    }

    for tramite in qs.only(
        "fecha_solicitud_tramite",
        "fecha_afectacion_padron",
    ):
        dias = (
            tramite.fecha_afectacion_padron
            - tramite.fecha_solicitud_tramite
        ).days

        if dias < 0:
            continue

        if dias <= 1:
            rangos["0-1"] += 1
        elif dias <= 3:
            rangos["2-3"] += 1
        elif dias <= 7:
            rangos["4-7"] += 1
        elif dias <= 15:
            rangos["8-15"] += 1
        elif dias <= 30:
            rangos["16-30"] += 1
        else:
            rangos["31+"] += 1

    return [
        {
            "rango": rango,
            "tramites": total,
        }
        for rango, total in rangos.items()
    ]


def _percentil(valores, percentil):
    if not valores:
        return None

    indice = (
        (len(valores) - 1)
        * percentil
        / 100
    )

    inferior = int(indice)

    superior = min(
        inferior + 1,
        len(valores) - 1,
    )

    fraccion = (
        indice - inferior
    )

    valor = (
        valores[inferior]
        + (
            valores[superior]
            - valores[inferior]
        )
        * fraccion
    )

    return round(
        valor,
        1,
    )
