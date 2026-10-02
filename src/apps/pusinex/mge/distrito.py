from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import transaction

from apps.pusinex.models import (
    CambioMGE,
    Distrito,
    Entidad,
)

from .registry import ruta_capa


def actualizar_distrito(
    raiz_bged,
    actualizacion,
):
    shape = ruta_capa(
        raiz_bged,
        "distrito",
    )

    ds = DataSource(str(shape))
    layer = ds[0]

    resultado = {
        "insertados": 0,
        "actualizados": 0,
        "sin_cambios": 0,
        "cambios_registrados": 0,
        "campos_modificados": {},
    }

    with transaction.atomic():
        for feature in layer:
            entidad_id = int(
                feature.get("entidad")
            )

            distrito_id = int(
                feature.get("distrito")
            )

            entidad = Entidad.objects.get(
                entidad=entidad_id
            )

            geom = feature.geom.geos
            geom.srid = 32614

            if geom.geom_type == "Polygon":
                geom = MultiPolygon(geom)
                geom.srid = 32614

            distrito = Distrito.objects.filter(
                distrito=distrito_id
            ).first()

            if distrito is None:
                raise ValueError(
                    f"El distrito {distrito_id:02} "
                    "existe en la BGD pero no existe "
                    "en la base de datos."
                )

            cambios = []

            if distrito.entidad_id != entidad_id:
                distrito.entidad = entidad
                cambios.append("entidad")

            geometria_cambio = (
                distrito.geom is None
                or not distrito.geom.equals(geom)
            )

            if geometria_cambio:
                geom_anterior = (
                    distrito.geom.clone()
                    if distrito.geom
                    else None
                )

                geom_nueva = geom.clone()

                CambioMGE.objects.create(
                    actualizacion=actualizacion,
                    capa="distrito",
                    clave=str(distrito_id),
                    tipo="GEOMETRIA",
                    geom_anterior=geom_anterior,
                    geom_nueva=geom_nueva,
                )

                resultado["cambios_registrados"] += 1

                distrito.geom = geom
                cambios.append("geom")

            if cambios:
                distrito.save(
                    update_fields=[
                        "entidad",
                        "geom",
                    ]
                )

                resultado["actualizados"] += 1

                resultado["campos_modificados"][
                    str(distrito_id)
                ] = cambios

            else:
                resultado["sin_cambios"] += 1

    return resultado
