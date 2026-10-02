from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import transaction

from apps.pusinex.models import (
    CambioMGE,
    Distrito,
    DistritoLocal,
    Entidad,
    Municipio,
    Seccion,
)

from .registry import ruta_capa


def actualizar_seccion(
    raiz_bged,
    actualizacion,
):
    shape = ruta_capa(
        raiz_bged,
        "seccion",
    )

    ds = DataSource(str(shape))
    layer = ds[0]

    resultado = {
        "insertados": 0,
        "actualizados": 0,
        "reactivados": 0,
        "desactivados": 0,
        "sin_cambios": 0,
        "cambios_registrados": 0,
        "campos_modificados": {},
    }

    secciones_bgd = set()

    with transaction.atomic():
        for feature in layer:
            entidad_id = int(
                feature.get("entidad")
            )

            distrito_id = int(
                feature.get("distrito")
            )

            distrito_local_id = int(
                feature.get("distrito_l")
            )

            municipio_id = int(
                feature.get("municipio")
            )

            seccion_id = int(
                feature.get("seccion")
            )

            tipo = int(
                feature.get("tipo")
            )

            secciones_bgd.add(
                seccion_id
            )

            entidad = Entidad.objects.get(
                entidad=entidad_id
            )

            distrito = Distrito.objects.get(
                distrito=distrito_id
            )

            distrito_local = (
                DistritoLocal.objects.get(
                    distrito_local=distrito_local_id
                )
            )

            municipio = Municipio.objects.get(
                municipio=municipio_id
            )

            geom = feature.geom.geos
            geom.srid = 32614

            if geom.geom_type == "Polygon":
                geom = MultiPolygon(geom)
                geom.srid = 32614

            seccion = Seccion.objects.filter(
                seccion=seccion_id
            ).first()

            # ---------------------------------
            # SECCIÓN NUEVA
            # ---------------------------------

            if seccion is None:
                seccion = Seccion.objects.create(
                    entidad=entidad,
                    distrito=distrito,
                    distrito_l=distrito_local,
                    municipio=municipio,
                    seccion=seccion_id,
                    tipo=tipo,
                    activa=True,
                    geom=geom,
                )

                CambioMGE.objects.create(
                    actualizacion=actualizacion,
                    capa="seccion",
                    clave=str(seccion_id),
                    tipo="ALTA",
                    geom_anterior=None,
                    geom_nueva=geom.clone(),
                )

                resultado["insertados"] += 1
                resultado["cambios_registrados"] += 1

                continue

            cambios = []

            # ---------------------------------
            # REACTIVACIÓN
            # ---------------------------------

            if not seccion.activa:
                seccion.activa = True
                cambios.append("activa")

                CambioMGE.objects.create(
                    actualizacion=actualizacion,
                    capa="seccion",
                    clave=str(seccion_id),
                    tipo="REACTIVACION",
                    geom_anterior=(
                        seccion.geom.clone()
                        if seccion.geom
                        else None
                    ),
                    geom_nueva=geom.clone(),
                )

                resultado["reactivados"] += 1
                resultado["cambios_registrados"] += 1

            # ---------------------------------
            # ADSCRIPCIONES
            # ---------------------------------

            if (
                seccion.entidad_id
                != entidad_id
            ):
                seccion.entidad = entidad
                cambios.append("entidad")

            if (
                seccion.distrito_id
                != distrito_id
            ):
                seccion.distrito = distrito
                cambios.append("distrito")

            if (
                seccion.distrito_l_id
                != distrito_local_id
            ):
                seccion.distrito_l = (
                    distrito_local
                )
                cambios.append(
                    "distrito_l"
                )

            if (
                seccion.municipio_id
                != municipio_id
            ):
                seccion.municipio = municipio
                cambios.append(
                    "municipio"
                )

            if seccion.tipo != tipo:
                seccion.tipo = tipo
                cambios.append("tipo")

            # ---------------------------------
            # GEOMETRÍA
            # ---------------------------------

            geometria_cambio = (
                seccion.geom is None
                or not seccion.geom.equals(
                    geom
                )
            )

            if geometria_cambio:
                geom_anterior = (
                    seccion.geom.clone()
                    if seccion.geom
                    else None
                )

                CambioMGE.objects.create(
                    actualizacion=actualizacion,
                    capa="seccion",
                    clave=str(seccion_id),
                    tipo="GEOMETRIA",
                    geom_anterior=geom_anterior,
                    geom_nueva=geom.clone(),
                )

                resultado[
                    "cambios_registrados"
                ] += 1

                seccion.geom = geom
                cambios.append("geom")

            # ---------------------------------
            # GUARDAR
            # ---------------------------------

            if cambios:
                seccion.save(
                    update_fields=[
                        "entidad",
                        "distrito",
                        "distrito_l",
                        "municipio",
                        "tipo",
                        "activa",
                        "geom",
                    ]
                )

                resultado[
                    "actualizados"
                ] += 1

                resultado[
                    "campos_modificados"
                ][str(seccion_id)] = cambios

            else:
                resultado[
                    "sin_cambios"
                ] += 1

        # -------------------------------------
        # DESACTIVAR SECCIONES AUSENTES
        # -------------------------------------

        secciones_a_desactivar = (
            Seccion.objects.filter(
                activa=True
            )
            .exclude(
                seccion__in=secciones_bgd
            )
        )

        for seccion in secciones_a_desactivar:
            CambioMGE.objects.create(
                actualizacion=actualizacion,
                capa="seccion",
                clave=str(
                    seccion.seccion
                ),
                tipo="BAJA",
                geom_anterior=(
                    seccion.geom.clone()
                    if seccion.geom
                    else None
                ),
                geom_nueva=None,
            )

            seccion.activa = False

            seccion.save(
                update_fields=[
                    "activa",
                ]
            )

            resultado[
                "desactivados"
            ] += 1

            resultado[
                "cambios_registrados"
            ] += 1

    return resultado
