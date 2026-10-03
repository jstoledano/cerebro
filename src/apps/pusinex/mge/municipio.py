from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import transaction

from apps.pusinex.models import (
    CambioMGE,
    Entidad,
    Municipio,
)

from .registry import ruta_capa
from .utils import geometria_cambio_informativo


def actualizar_municipio(
    raiz_bged,
    actualizacion,
):
    # ---------------------------------
    # ABRIR CAPA BGD
    # ---------------------------------

    shape = ruta_capa(
        raiz_bged,
        "municipio",
    )

    ds = DataSource(str(shape))
    layer = ds[0]

    # ---------------------------------
    # RESULTADO DE LA ACTUALIZACIÓN
    # ---------------------------------

    resultado = {
        "insertados": 0,
        "actualizados": 0,
        "sin_cambios": 0,
        "cambios_registrados": 0,
        "campos_modificados": {},
    }

    # ---------------------------------
    # PROCESAR MUNICIPIOS
    # ---------------------------------

    with transaction.atomic():
        for feature in layer:
            # ---------------------------------
            # ATRIBUTOS DE LA BGD
            # ---------------------------------

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

            # ---------------------------------
            # GEOMETRÍA DE LA BGD
            # ---------------------------------

            geom = feature.geom.geos
            geom.srid = 32614

            if geom.geom_type == "Polygon":
                geom = MultiPolygon(geom)
                geom.srid = 32614

            # ---------------------------------
            # MUNICIPIO ACTUAL EN LA BD
            # ---------------------------------

            municipio = Municipio.objects.filter(
                municipio=municipio_id
            ).first()

            # ---------------------------------
            # MUNICIPIO NUEVO
            # ---------------------------------

            if municipio is None:
                Municipio.objects.create(
                    municipio=municipio_id,
                    entidad=entidad,
                    nombre=nombre,
                    geom=geom,
                )

                resultado[
                    "insertados"
                ] += 1

                continue

            cambios = []

            # ---------------------------------
            # ADSCRIPCIÓN A ENTIDAD
            # ---------------------------------

            if municipio.entidad_id != entidad_id:
                municipio.entidad = entidad
                cambios.append("entidad")

            # ---------------------------------
            # NOMBRE
            # ---------------------------------

            if municipio.nombre != nombre:
                municipio.nombre = nombre
                cambios.append("nombre")

            # ---------------------------------
            # GEOMETRÍA
            #
            # geometria_distinta:
            # determina si la geometría vigente
            # debe sincronizarse con la BGD.
            #
            # cambio_informativo:
            # determina si la diferencia merece
            # registrarse en CambioMGE.
            # ---------------------------------

            geometria_distinta = (
                municipio.geom is None
                or not municipio.geom.equals_exact(
                    geom,
                    0.0,
                )
            )

            cambio_informativo = (
                geometria_cambio_informativo(
                    municipio.geom,
                    geom,
                )
            )

            # ---------------------------------
            # REGISTRAR CAMBIO INFORMATIVO
            # ---------------------------------

            if cambio_informativo:
                geom_anterior = (
                    municipio.geom.clone()
                    if municipio.geom
                    else None
                )

                CambioMGE.objects.create(
                    actualizacion=actualizacion,
                    capa="municipio",
                    clave=str(municipio_id),
                    tipo="GEOMETRIA",
                    geom_anterior=geom_anterior,
                    geom_nueva=geom.clone(),
                )

                resultado[
                    "cambios_registrados"
                ] += 1

            # ---------------------------------
            # SINCRONIZAR GEOMETRÍA VIGENTE
            # ---------------------------------

            if geometria_distinta:
                municipio.geom = geom
                cambios.append("geom")

            # ---------------------------------
            # GUARDAR CAMBIOS
            # ---------------------------------

            if cambios:
                municipio.save(
                    update_fields=[
                        "entidad",
                        "nombre",
                        "geom",
                    ]
                )

                resultado[
                    "actualizados"
                ] += 1

                resultado[
                    "campos_modificados"
                ][str(municipio_id)] = cambios

            else:
                resultado[
                    "sin_cambios"
                ] += 1

    # ---------------------------------
    # RESULTADO FINAL
    # ---------------------------------

    return resultado
