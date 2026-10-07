from django.contrib.gis.gdal import DataSource
from django.db import transaction

from apps.pusinex.models import Localidad, Seccion

from .registry import ruta_capa


def actualizar_localidad(raiz_bged):
    # ---------------------------------
    # ABRIR CAPA BGD
    # ---------------------------------

    shape = ruta_capa(
        raiz_bged,
        "localidad",
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
    # LOCALIDADES ACTUALES EN MEMORIA
    # ---------------------------------

    localidades_actuales = {
        (
            localidad.seccion_id,
            localidad.localidad,
        ): localidad
        for localidad in Localidad.objects.all()
    }

    claves_bgd = set()

    localidades_a_crear = []
    localidades_a_actualizar = []

    # ---------------------------------
    # PROCESAR BGD
    # ---------------------------------

    with transaction.atomic():
        for feature in layer:
            seccion_id = int(
                feature.get("seccion")
            )

            localidad_id = int(
                feature.get("localidad")
            )

            clave = (
                seccion_id,
                localidad_id,
            )

            claves_bgd.add(clave)

            # ---------------------------------
            # VALIDAR SECCIÓN
            # ---------------------------------

            seccion = secciones.get(
                seccion_id
            )

            if seccion is None:
                raise ValueError(
                    f"La localidad "
                    f"{seccion_id:04}-"
                    f"{localidad_id:04} "
                    "pertenece a una sección "
                    "que no existe en la base."
                )

            # ---------------------------------
            # ATRIBUTOS
            # ---------------------------------

            nombre = str(
                feature.get("nombre")
            ).strip()

            tipo = int(
                feature.get("tipo")
            )

            cabecera = int(
                feature.get("cabecera")
            )

            status = int(
                feature.get("status")
            )

            control = int(
                feature.get("control")
            )

            id_bgd = int(
                feature.get("id")
            )

            # ---------------------------------
            # GEOMETRÍA
            # ---------------------------------

            geom = feature.geom.geos
            geom.srid = 32614

            # ---------------------------------
            # LOCALIDAD NUEVA
            # ---------------------------------

            localidad = localidades_actuales.get(
                clave
            )

            if localidad is None:
                localidades_a_crear.append(
                    Localidad(
                        seccion=seccion,
                        localidad=localidad_id,
                        nombre=nombre,
                        tipo=tipo,
                        cabecera=cabecera,
                        status=status,
                        control=control,
                        id_bgd=id_bgd,
                        geom=geom,
                    )
                )

                resultado["insertados"] += 1
                continue

            # ---------------------------------
            # LOCALIDAD EXISTENTE
            # ---------------------------------

            cambios = False

            if localidad.nombre != nombre:
                localidad.nombre = nombre
                cambios = True

            if localidad.tipo != tipo:
                localidad.tipo = tipo
                cambios = True

            if localidad.cabecera != cabecera:
                localidad.cabecera = cabecera
                cambios = True

            if localidad.status != status:
                localidad.status = status
                cambios = True

            if localidad.control != control:
                localidad.control = control
                cambios = True

            if localidad.id_bgd != id_bgd:
                localidad.id_bgd = id_bgd
                cambios = True

            geometria_distinta = (
                localidad.geom is None
                or not localidad.geom.equals_exact(
                    geom,
                    0.0,
                )
            )

            if geometria_distinta:
                localidad.geom = geom
                cambios = True

            if cambios:
                localidades_a_actualizar.append(
                    localidad
                )
                resultado["actualizados"] += 1
            else:
                resultado["sin_cambios"] += 1

        # ---------------------------------
        # CREAR
        # ---------------------------------

        if localidades_a_crear:
            Localidad.objects.bulk_create(
                localidades_a_crear,
                batch_size=1000,
            )

        # ---------------------------------
        # ACTUALIZAR
        # ---------------------------------

        if localidades_a_actualizar:
            Localidad.objects.bulk_update(
                localidades_a_actualizar,
                [
                    "nombre",
                    "tipo",
                    "cabecera",
                    "status",
                    "control",
                    "id_bgd",
                    "geom",
                ],
                batch_size=1000,
            )

        # ---------------------------------
        # ELIMINAR AUSENTES
        # ---------------------------------

        ids_a_eliminar = [
            localidad.pk
            for clave, localidad
            in localidades_actuales.items()
            if clave not in claves_bgd
        ]

        if ids_a_eliminar:
            resultado["eliminados"] = len(
                ids_a_eliminar
            )

            Localidad.objects.filter(
                pk__in=ids_a_eliminar
            ).delete()

    return resultado
