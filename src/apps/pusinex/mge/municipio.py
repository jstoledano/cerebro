from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import transaction

from apps.pusinex.models import (
    CambioMGE,
    Entidad,
    Municipio,
)

from .registry import ruta_capa


def actualizar_municipio(
    raiz_bged,
    actualizacion,
):
    shape = ruta_capa(
        raiz_bged,
        "municipio",
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

            municipio_id = int(
                feature.get("municipio")
            )

            nombre = str(
                feature.get("nombre")
            ).strip()

            entidad = Entidad.objects.get(
                entidad=entidad_id
            )

            geom = feature.geom.geos
            geom.srid = 32614

            if geom.geom_type == "Polygon":
                geom = MultiPolygon(geom)
                geom.srid = 32614

            municipio = Municipio.objects.filter(
                municipio=municipio_id
            ).first()

            if municipio is None:
                Municipio.objects.create(
                    municipio=municipio_id,
                    entidad=entidad,
                    nombre=nombre,
                    geom=geom,
                )

                resultado["insertados"] += 1
                continue

            cambios = []

            if municipio.entidad_id != entidad_id:
                municipio.entidad = entidad
                cambios.append("entidad")

            if municipio.nombre != nombre:
                municipio.nombre = nombre
                cambios.append("nombre")

            geometria_cambio = (
                municipio.geom is None
                or not municipio.geom.equals(geom)
            )

            if geometria_cambio:
                geom_anterior = (
                    municipio.geom.clone()
                    if municipio.geom
                    else None
                )

                geom_nueva = geom.clone()

                CambioMGE.objects.create(
                    actualizacion=actualizacion,
                    capa="municipio",
                    clave=str(municipio_id),
                    tipo="GEOMETRIA",
                    geom_anterior=geom_anterior,
                    geom_nueva=geom_nueva,
                )

                resultado["cambios_registrados"] += 1

                municipio.geom = geom
                cambios.append("geom")

            if cambios:
                municipio.save(
                    update_fields=[
                        "entidad",
                        "nombre",
                        "geom",
                    ]
                )

                resultado["actualizados"] += 1

                resultado["campos_modificados"][
                    str(municipio_id)
                ] = cambios

            else:
                resultado["sin_cambios"] += 1

    return resultado
