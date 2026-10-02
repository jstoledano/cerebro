from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import transaction

from apps.pusinex.models import Entidad

from .registry import ruta_capa


def actualizar_entidad(raiz_bged):
    shape = ruta_capa(raiz_bged, "entidad")

    ds = DataSource(str(shape))
    layer = ds[0]
    feature = layer[0]

    entidad_id = int(feature.get("entidad"))
    nombre = str(feature.get("nombre")).strip()

    campos = set(layer.fields)

    if "circunscri" in campos:
        valor = feature.get("circunscri")
        circunscripcion = int(valor) if valor not in (None, "") else 4
    else:
        circunscripcion = 4

    geom = feature.geom.geos
    geom.srid = 32614

    if geom.geom_type == "Polygon":
        geom = MultiPolygon(geom)
        geom.srid = 32614

    with transaction.atomic():
        entidad = Entidad.objects.filter(
            entidad=entidad_id
        ).first()

        if entidad is None:
            Entidad.objects.create(
                entidad=entidad_id,
                nombre=nombre,
                circunscripcion=circunscripcion,
                geom=geom,
            )

            return {
                "insertados": 1,
                "actualizados": 0,
                "sin_cambios": 0,
            }

        cambios = []

        if entidad.nombre != nombre:
            entidad.nombre = nombre
            cambios.append("nombre")

        if entidad.circunscripcion != circunscripcion:
            entidad.circunscripcion = circunscripcion
            cambios.append("circunscripcion")

        if (
            entidad.geom is None
            or not entidad.geom.equals_exact(geom, 0.0)
        ):
            entidad.geom = geom
            cambios.append("geom")

        if cambios:
            entidad.save(
                update_fields=[
                    "nombre",
                    "circunscripcion",
                    "geom",
                ]
            )

            return {
                "insertados": 0,
                "actualizados": 1,
                "sin_cambios": 0,
                "campos_modificados": cambios,
            }

        return {
            "insertados": 0,
            "actualizados": 0,
            "sin_cambios": 1,
        }
