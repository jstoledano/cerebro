from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import transaction

from apps.pusinex.models import (
    CambioMGE,
    DistritoLocal,
    Entidad,
)

from .registry import ruta_capa


def actualizar_distrito_local(
    raiz_bged,
    actualizacion,
):
    shape = ruta_capa(
        raiz_bged,
        "distrito_local",
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

            distrito_local_id = int(
                feature.get("distrito_l")
            )

            entidad = Entidad.objects.get(
                entidad=entidad_id
            )

            geom = feature.geom.geos
            geom.srid = 32614

            if geom.geom_type == "Polygon":
                geom = MultiPolygon(geom)
                geom.srid = 32614

            distrito_local = (
                DistritoLocal.objects.filter(
                    distrito_local=distrito_local_id
                ).first()
            )

            if distrito_local is None:
                raise ValueError(
                    f"El distrito local "
                    f"{distrito_local_id:02} "
                    "existe en la BGD pero no existe "
                    "en la base de datos."
                )

            cambios = []

            if distrito_local.entidad_id != entidad_id:
                distrito_local.entidad = entidad
                cambios.append("entidad")

            geometria_cambio = (
                distrito_local.geom is None
                or not distrito_local.geom.equals(geom)
            )

            if geometria_cambio:
                geom_anterior = (
                    distrito_local.geom.clone()
                    if distrito_local.geom
                    else None
                )

                geom_nueva = geom.clone()

                CambioMGE.objects.create(
                    actualizacion=actualizacion,
                    capa="distrito_local",
                    clave=str(distrito_local_id),
                    tipo="GEOMETRIA",
                    geom_anterior=geom_anterior,
                    geom_nueva=geom_nueva,
                )

                resultado["cambios_registrados"] += 1

                distrito_local.geom = geom
                cambios.append("geom")

            if cambios:
                distrito_local.save(
                    update_fields=[
                        "entidad",
                        "geom",
                    ]
                )

                resultado["actualizados"] += 1

                resultado["campos_modificados"][
                    str(distrito_local_id)
                ] = cambios

            else:
                resultado["sin_cambios"] += 1

    return resultado
