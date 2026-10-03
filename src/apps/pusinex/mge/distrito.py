from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import transaction

from apps.pusinex.models import (
    CambioMGE,
    Distrito,
    Entidad,
)

from .registry import ruta_capa
from .utils import geometria_cambio_informativo


def actualizar_distrito(
    raiz_bged,
    actualizacion,
):
    # ---------------------------------
    # ABRIR CAPA BGD
    # ---------------------------------

    shape = ruta_capa(
        raiz_bged,
        "distrito",
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
    # PROCESAR DISTRITOS
    # ---------------------------------

    with transaction.atomic():
        for feature in layer:
            # ---------------------------------
            # ATRIBUTOS DE LA BGD
            # ---------------------------------

            entidad_id = int(
                feature.get("entidad")
            )

            distrito_id = int(
                feature.get("distrito")
            )

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
            # DISTRITO ACTUAL EN LA BD
            # ---------------------------------

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

            # ---------------------------------
            # ADSCRIPCIÓN A ENTIDAD
            # ---------------------------------

            if distrito.entidad_id != entidad_id:
                distrito.entidad = entidad
                cambios.append("entidad")

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
                distrito.geom is None
                or not distrito.geom.equals_exact(
                    geom,
                    0.0,
                )
            )

            cambio_informativo = (
                geometria_cambio_informativo(
                    distrito.geom,
                    geom,
                )
            )

            # ---------------------------------
            # REGISTRAR CAMBIO INFORMATIVO
            # ---------------------------------

            if cambio_informativo:
                geom_anterior = (
                    distrito.geom.clone()
                    if distrito.geom
                    else None
                )

                CambioMGE.objects.create(
                    actualizacion=actualizacion,
                    capa="distrito",
                    clave=str(distrito_id),
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
                distrito.geom = geom
                cambios.append("geom")

            # ---------------------------------
            # GUARDAR CAMBIOS
            # ---------------------------------

            if cambios:
                distrito.save(
                    update_fields=[
                        "entidad",
                        "geom",
                    ]
                )

                resultado[
                    "actualizados"
                ] += 1

                resultado[
                    "campos_modificados"
                ][str(distrito_id)] = cambios

            else:
                resultado[
                    "sin_cambios"
                ] += 1

    # ---------------------------------
    # RESULTADO FINAL
    # ---------------------------------

    return resultado
