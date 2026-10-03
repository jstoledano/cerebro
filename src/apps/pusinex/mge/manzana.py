from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import transaction

from apps.pusinex.models import Manzana, Seccion

from .registry import ruta_capa


def actualizar_manzana(raiz_bged):
    # ---------------------------------
    # ABRIR CAPA BGD
    # ---------------------------------

    shape = ruta_capa(
        raiz_bged,
        "manzana",
    )

    ds = DataSource(str(shape))
    layer = ds[0]

    # ---------------------------------
    # RESULTADO
    # ---------------------------------

    resultado = {
        "insertados": 0,
        "actualizados": 0,
        "eliminados": 0,
        "sin_cambios": 0,
    }

    # ---------------------------------
    # SECCIONES EN MEMORIA
    # ---------------------------------

    secciones = {
        seccion.seccion: seccion
        for seccion in Seccion.objects.all()
    }

    # ---------------------------------
    # MANZANAS ACTUALES EN MEMORIA
    # ---------------------------------

    manzanas_actuales = {
        (
            manzana.seccion_id,
            manzana.localidad,
            manzana.manzana,
        ): manzana
        for manzana in Manzana.objects.all()
    }

    claves_bgd = set()

    manzanas_a_crear = []
    manzanas_a_actualizar = []

    # ---------------------------------
    # PROCESAR BGD
    # ---------------------------------

    with transaction.atomic():
        for feature in layer:
            # ---------------------------------
            # ATRIBUTOS DE LA BGD
            # ---------------------------------

            seccion_id = int(
                feature.get("seccion")
            )

            localidad_id = int(
                feature.get("localidad")
            )

            manzana_id = int(
                feature.get("manzana")
            )

            clave = (
                seccion_id,
                localidad_id,
                manzana_id,
            )

            claves_bgd.add(clave)

            # ---------------------------------
            # VALIDAR EXISTENCIA DE SECCIÓN
            # ---------------------------------

            seccion = secciones.get(
                seccion_id
            )

            if seccion is None:
                raise ValueError(
                    f"La manzana "
                    f"{seccion_id:04}-"
                    f"{localidad_id:03}-"
                    f"{manzana_id:03} "
                    "pertenece a una sección "
                    "que no existe en la base."
                )

            # ---------------------------------
            # GEOMETRÍA
            # ---------------------------------

            geom = feature.geom.geos
            geom.srid = 32614

            if geom.geom_type == "Polygon":
                geom = MultiPolygon(geom)
                geom.srid = 32614

            # ---------------------------------
            # MANZANA NUEVA
            # ---------------------------------

            manzana = manzanas_actuales.get(
                clave
            )

            if manzana is None:
                manzanas_a_crear.append(
                    Manzana(
                        seccion=seccion,
                        localidad=localidad_id,
                        manzana=manzana_id,
                        geom=geom,
                    )
                )

                resultado["insertados"] += 1
                continue

            # ---------------------------------
            # MANZANA EXISTENTE
            # ---------------------------------

            geometria_distinta = (
                manzana.geom is None
                or not manzana.geom.equals_exact(
                    geom,
                    0.0,
                )
            )

            if geometria_distinta:
                manzana.geom = geom

                manzanas_a_actualizar.append(
                    manzana
                )

                resultado["actualizados"] += 1
            else:
                resultado["sin_cambios"] += 1

        # ---------------------------------
        # CREAR NUEVAS
        # ---------------------------------

        if manzanas_a_crear:
            Manzana.objects.bulk_create(
                manzanas_a_crear,
                batch_size=1000,
            )

        # ---------------------------------
        # ACTUALIZAR GEOMETRÍAS
        # ---------------------------------

        if manzanas_a_actualizar:
            Manzana.objects.bulk_update(
                manzanas_a_actualizar,
                ["geom"],
                batch_size=1000,
            )

        # ---------------------------------
        # ELIMINAR AUSENTES EN LA BGD
        # ---------------------------------

        ids_a_eliminar = [
            manzana.pk
            for clave, manzana
            in manzanas_actuales.items()
            if clave not in claves_bgd
        ]

        if ids_a_eliminar:
            resultado["eliminados"] = len(
                ids_a_eliminar
            )

            Manzana.objects.filter(
                pk__in=ids_a_eliminar
            ).delete()

    # ---------------------------------
    # RESULTADO FINAL
    # ---------------------------------

    return resultado
