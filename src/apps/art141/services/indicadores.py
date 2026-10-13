import math
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


def get_desempeno_entrega(anio=None):
    qs = _queryset(anio)

    con_entrega = qs.exclude(
        fecha_entrega_credencial__isnull=True
    )

    sin_entrega = qs.filter(
        fecha_entrega_credencial__isnull=True
    ).count()

    dias_entrega = []

    for tramite in con_entrega.only(
        "fecha_solicitud_tramite",
        "fecha_entrega_credencial",
    ):
        if (
            tramite.fecha_solicitud_tramite is None
            or tramite.fecha_entrega_credencial is None
        ):
            continue

        dias = (
            tramite.fecha_entrega_credencial
            - tramite.fecha_solicitud_tramite
        ).days

        if dias >= 0:
            dias_entrega.append(dias)

    dias_entrega.sort()

    total_medidos = len(dias_entrega)

    hasta_30 = sum(
        1
        for dias in dias_entrega
        if dias <= 30
    )

    hasta_90 = sum(
        1
        for dias in dias_entrega
        if dias <= 90
    )

    return {
        "casos": total_medidos,
        "sin_fecha_entrega": sin_entrega,
        "mediana": (
            _mediana(dias_entrega)
            if dias_entrega
            else None
        ),
        "hasta_30": hasta_30,
        "hasta_90": hasta_90,
        "porcentaje_30": (
            round(
                hasta_30 * 100 / total_medidos,
                1,
            )
            if total_medidos
            else 0
        ),
        "porcentaje_90": (
            round(
                hasta_90 * 100 / total_medidos,
                1,
            )
            if total_medidos
            else 0
        ),
    }


def get_distribucion_dias_entrega(anio=None):
    qs = (
        _queryset(anio)
        .exclude(fecha_solicitud_tramite__isnull=True)
        .exclude(fecha_entrega_credencial__isnull=True)
    )

    dias_observados = []

    for tramite in qs.only(
        "fecha_solicitud_tramite",
        "fecha_entrega_credencial",
    ):
        dias = (
            tramite.fecha_entrega_credencial
            - tramite.fecha_solicitud_tramite
        ).days

        if dias >= 0:
            dias_observados.append(dias)

    if not dias_observados:
        return []

    maximo_observado = max(dias_observados)

    limite_superior = (
        math.ceil(maximo_observado / 5) * 5
    )

    intervalos = []

    minimo = 0

    while minimo <= limite_superior:
        maximo = 5 if minimo == 0 else minimo + 4

        intervalos.append(
            (minimo, maximo)
        )

        minimo = maximo + 1

    frecuencias = []

    for minimo, maximo in intervalos:
        total = sum(
            1
            for dias in dias_observados
            if minimo <= dias <= maximo
        )

        frecuencias.append(
            {
                "rango": f"{minimo}-{maximo}",
                "tramites": total,
                "centro": (minimo + maximo) / 2,
            }
        )

    if len(dias_observados) < 2:
        for item in frecuencias:
            item["normal"] = 0

        return frecuencias

    cantidad = len(dias_observados)

    media = sum(dias_observados) / cantidad

    varianza = sum(
        (dias - media) ** 2
        for dias in dias_observados
    ) / cantidad

    desviacion = math.sqrt(varianza)

    if desviacion == 0:
        for item in frecuencias:
            item["normal"] = 0

        return frecuencias

    ancho_intervalo = 5

    for item in frecuencias:
        x = item["centro"]

        densidad = (
            1
            / (
                desviacion
                * math.sqrt(2 * math.pi)
            )
        ) * math.exp(
            -0.5
            * (
                (x - media)
                / desviacion
            ) ** 2
        )

        item["normal"] = round(
            densidad
            * cantidad
            * ancho_intervalo,
            2,
        )

    return frecuencias

def _mediana(valores):
    cantidad = len(valores)

    if cantidad == 0:
        return None

    mitad = cantidad // 2

    if cantidad % 2:
        return valores[mitad]

    return round(
        (
            valores[mitad - 1]
            + valores[mitad]
        )
        / 2,
        1,
    )
