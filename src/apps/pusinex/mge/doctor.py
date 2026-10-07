from django.contrib.gis.gdal import DataSource

from apps.pusinex.models import (
    Distrito,
    DistritoLocal,
    Municipio,
)

from .registry import (
    CAPAS,
    ENTIDAD_INE,
    ruta_capa,
)

def revisar_entidad(raiz_bged):
    resultado = {
        "capa": "entidad",
        "apto": True,
        "comprobaciones": [],
        "errores": [],
    }

    shape = ruta_capa(raiz_bged, "entidad")
    base = shape.with_suffix("")

    archivos = {
        ".shp": base.with_suffix(".shp"),
        ".shx": base.with_suffix(".shx"),
        ".dbf": base.with_suffix(".dbf"),
        ".prj": base.with_suffix(".prj"),
    }

    for extension, ruta in archivos.items():
        existe = ruta.exists()

        resultado["comprobaciones"].append(
            {
                "prueba": f"Archivo {extension}",
                "ok": existe,
                "detalle": str(ruta),
            }
        )

        if not existe:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Falta el archivo requerido: {ruta}"
            )

    if not resultado["apto"]:
        return resultado

    try:
        ds = DataSource(str(shape))
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir el shapefile: {exc}"
        )
        return resultado

    if len(ds) != 1:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba una capa y se encontraron {len(ds)}."
        )
        return resultado

    layer = ds[0]

    cantidad = len(layer)

    resultado["comprobaciones"].append(
        {
            "prueba": "Cantidad de registros",
            "ok": cantidad == 1,
            "detalle": cantidad,
        }
    )

    if cantidad != 1:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Entidad debe contener exactamente un registro; contiene {cantidad}."
        )

    campos = set(layer.fields)
    requeridos = CAPAS["entidad"]["campos_obligatorios"]
    faltantes = requeridos - campos

    resultado["comprobaciones"].append(
        {
            "prueba": "Campos obligatorios",
            "ok": not faltantes,
            "detalle": sorted(campos),
        }
    )

    if faltantes:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Faltan campos obligatorios: {', '.join(sorted(faltantes))}"
        )

    srid = layer.srs.srid if layer.srs else None

    resultado["comprobaciones"].append(
        {
            "prueba": "SRID",
            "ok": srid == 32614,
            "detalle": srid,
        }
    )

    if srid != 32614:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba EPSG:32614 y se encontró {srid}."
        )

    if cantidad == 1 and not faltantes:
        feature = layer[0]

        entidad = int(feature.get("entidad"))

        resultado["comprobaciones"].append(
            {
                "prueba": "Clave de entidad",
                "ok": entidad == ENTIDAD_INE,
                "detalle": entidad,
            }
        )

        if entidad != ENTIDAD_INE:
            resultado["apto"] = False
            resultado["errores"].append(
                f"La BGD corresponde a la entidad {entidad}; se esperaba {ENTIDAD_INE}."
            )

        geom = feature.geom.geos
        geom.srid = 32614

        tipo = geom.geom_type

        tipo_valido = tipo in ("Polygon", "MultiPolygon")

        resultado["comprobaciones"].append(
            {
                "prueba": "Tipo de geometría",
                "ok": tipo_valido,
                "detalle": tipo,
            }
        )

        if not tipo_valido:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Geometría inesperada: {tipo}."
            )

        resultado["comprobaciones"].append(
            {
                "prueba": "Geometría válida",
                "ok": geom.valid,
                "detalle": geom.valid_reason,
            }
        )

        if not geom.valid:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Geometría inválida: {geom.valid_reason}"
            )

    return resultado

def revisar_distrito(raiz_bged):
    resultado = {
        "capa": "distrito",
        "apto": True,
        "comprobaciones": [],
        "errores": [],
    }

    shape = ruta_capa(raiz_bged, "distrito")
    base = shape.with_suffix("")

    archivos = {
        ".shp": base.with_suffix(".shp"),
        ".shx": base.with_suffix(".shx"),
        ".dbf": base.with_suffix(".dbf"),
        ".prj": base.with_suffix(".prj"),
    }

    for extension, ruta in archivos.items():
        existe = ruta.exists()

        resultado["comprobaciones"].append(
            {
                "prueba": f"Archivo {extension}",
                "ok": existe,
                "detalle": str(ruta),
            }
        )

        if not existe:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Falta el archivo requerido: {ruta}"
            )

    if not resultado["apto"]:
        return resultado

    try:
        ds = DataSource(str(shape))
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir el shapefile: {exc}"
        )
        return resultado

    if len(ds) != 1:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba una capa y se encontraron {len(ds)}."
        )
        return resultado

    layer = ds[0]

    cantidad = len(layer)

    resultado["comprobaciones"].append(
        {
            "prueba": "Cantidad de registros",
            "ok": cantidad == 3,
            "detalle": cantidad,
        }
    )

    if cantidad != 3:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaban 3 distritos y se encontraron {cantidad}."
        )

    campos = set(layer.fields)
    requeridos = CAPAS["distrito"]["campos_obligatorios"]
    faltantes = requeridos - campos

    resultado["comprobaciones"].append(
        {
            "prueba": "Campos obligatorios",
            "ok": not faltantes,
            "detalle": sorted(campos),
        }
    )

    if faltantes:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Faltan campos obligatorios: {', '.join(sorted(faltantes))}"
        )

    srid = layer.srs.srid if layer.srs else None

    resultado["comprobaciones"].append(
        {
            "prueba": "SRID",
            "ok": srid == 32614,
            "detalle": srid,
        }
    )

    if srid != 32614:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba EPSG:32614 y se encontró {srid}."
        )

    distritos = set()

    for feature in layer:
        entidad = int(feature.get("entidad"))
        distrito = int(feature.get("distrito"))

        distritos.add(distrito)

        if entidad != ENTIDAD_INE:
            resultado["apto"] = False
            resultado["errores"].append(
                f"El distrito {distrito} pertenece a la entidad {entidad}."
            )

        geom = feature.geom.geos
        geom.srid = 32614

        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            resultado["apto"] = False
            resultado["errores"].append(
                f"Distrito {distrito}: geometría inesperada {geom.geom_type}."
            )

        if not geom.valid:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Distrito {distrito}: geometría inválida."
            )

    esperados = {1, 2, 3}

    resultado["comprobaciones"].append(
        {
            "prueba": "Claves de distrito",
            "ok": distritos == esperados,
            "detalle": sorted(distritos),
        }
    )

    if distritos != esperados:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaban los distritos {sorted(esperados)} y se encontraron {sorted(distritos)}."
        )

    return resultado

def revisar_distrito_local(raiz_bged):
    resultado = {
        "capa": "distrito_local",
        "apto": True,
        "comprobaciones": [],
        "errores": [],
    }

    shape = ruta_capa(
        raiz_bged,
        "distrito_local",
    )
    base = shape.with_suffix("")

    archivos = {
        ".shp": base.with_suffix(".shp"),
        ".shx": base.with_suffix(".shx"),
        ".dbf": base.with_suffix(".dbf"),
        ".prj": base.with_suffix(".prj"),
    }

    for extension, ruta in archivos.items():
        existe = ruta.exists()

        resultado["comprobaciones"].append(
            {
                "prueba": f"Archivo {extension}",
                "ok": existe,
                "detalle": str(ruta),
            }
        )

        if not existe:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Falta el archivo requerido: {ruta}"
            )

    if not resultado["apto"]:
        return resultado

    try:
        ds = DataSource(str(shape))
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir el shapefile: {exc}"
        )
        return resultado

    if len(ds) != 1:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba una capa y se encontraron {len(ds)}."
        )
        return resultado

    layer = ds[0]

    cantidad = len(layer)

    resultado["comprobaciones"].append(
        {
            "prueba": "Cantidad de registros",
            "ok": cantidad == 15,
            "detalle": cantidad,
        }
    )

    if cantidad != 15:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaban 15 distritos locales "
            f"y se encontraron {cantidad}."
        )

    campos = set(layer.fields)
    requeridos = CAPAS[
        "distrito_local"
    ]["campos_obligatorios"]

    faltantes = requeridos - campos

    resultado["comprobaciones"].append(
        {
            "prueba": "Campos obligatorios",
            "ok": not faltantes,
            "detalle": sorted(campos),
        }
    )

    if faltantes:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Faltan campos obligatorios: "
            f"{', '.join(sorted(faltantes))}"
        )

    srid = layer.srs.srid if layer.srs else None

    resultado["comprobaciones"].append(
        {
            "prueba": "SRID",
            "ok": srid == 32614,
            "detalle": srid,
        }
    )

    if srid != 32614:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba EPSG:32614 "
            f"y se encontró {srid}."
        )

    claves = set()

    for feature in layer:
        entidad = int(
            feature.get("entidad")
        )

        distrito_local = int(
            feature.get("distrito_l")
        )

        claves.add(distrito_local)

        if entidad != ENTIDAD_INE:
            resultado["apto"] = False
            resultado["errores"].append(
                f"El distrito local "
                f"{distrito_local:02} pertenece "
                f"a la entidad {entidad}."
            )

        geom = feature.geom.geos
        geom.srid = 32614

        if geom.geom_type not in (
            "Polygon",
            "MultiPolygon",
        ):
            resultado["apto"] = False
            resultado["errores"].append(
                f"Distrito local "
                f"{distrito_local:02}: "
                f"geometría inesperada "
                f"{geom.geom_type}."
            )

        if not geom.valid:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Distrito local "
                f"{distrito_local:02}: "
                "geometría inválida."
            )

    esperados = set(range(1, 16))

    resultado["comprobaciones"].append(
        {
            "prueba": "Claves de distrito local",
            "ok": claves == esperados,
            "detalle": sorted(claves),
        }
    )

    if claves != esperados:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaban los distritos locales "
            f"{sorted(esperados)} y se encontraron "
            f"{sorted(claves)}."
        )

    return resultado

def revisar_municipio(raiz_bged):
    resultado = {
        "capa": "municipio",
        "apto": True,
        "comprobaciones": [],
        "errores": [],
    }

    shape = ruta_capa(
        raiz_bged,
        "municipio",
    )
    base = shape.with_suffix("")

    archivos = {
        ".shp": base.with_suffix(".shp"),
        ".shx": base.with_suffix(".shx"),
        ".dbf": base.with_suffix(".dbf"),
        ".prj": base.with_suffix(".prj"),
    }

    for extension, ruta in archivos.items():
        existe = ruta.exists()

        resultado["comprobaciones"].append(
            {
                "prueba": f"Archivo {extension}",
                "ok": existe,
                "detalle": str(ruta),
            }
        )

        if not existe:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Falta el archivo requerido: {ruta}"
            )

    if not resultado["apto"]:
        return resultado

    try:
        ds = DataSource(str(shape))
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir el shapefile: {exc}"
        )
        return resultado

    if len(ds) != 1:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba una capa y se encontraron {len(ds)}."
        )
        return resultado

    layer = ds[0]
    cantidad = len(layer)

    resultado["comprobaciones"].append(
        {
            "prueba": "Cantidad de registros",
            "ok": cantidad == 60,
            "detalle": cantidad,
        }
    )

    if cantidad != 60:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaban 60 municipios "
            f"y se encontraron {cantidad}."
        )

    campos = set(layer.fields)

    requeridos = CAPAS[
        "municipio"
    ]["campos_obligatorios"]

    faltantes = requeridos - campos

    resultado["comprobaciones"].append(
        {
            "prueba": "Campos obligatorios",
            "ok": not faltantes,
            "detalle": sorted(campos),
        }
    )

    if faltantes:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Faltan campos obligatorios: "
            f"{', '.join(sorted(faltantes))}"
        )

    srid = layer.srs.srid if layer.srs else None

    resultado["comprobaciones"].append(
        {
            "prueba": "SRID",
            "ok": srid == 32614,
            "detalle": srid,
        }
    )

    if srid != 32614:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba EPSG:32614 "
            f"y se encontró {srid}."
        )

    claves = set()

    for feature in layer:
        entidad = int(
            feature.get("entidad")
        )

        municipio = int(
            feature.get("municipio")
        )

        claves.add(municipio)

        if entidad != ENTIDAD_INE:
            resultado["apto"] = False
            resultado["errores"].append(
                f"El municipio {municipio:03} "
                f"pertenece a la entidad "
                f"{entidad}."
            )

        geom = feature.geom.geos
        geom.srid = 32614

        if geom.geom_type not in (
            "Polygon",
            "MultiPolygon",
        ):
            resultado["apto"] = False
            resultado["errores"].append(
                f"Municipio {municipio:03}: "
                f"geometría inesperada "
                f"{geom.geom_type}."
            )

        if not geom.valid:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Municipio {municipio:03}: "
                "geometría inválida."
            )

    resultado["comprobaciones"].append(
        {
            "prueba": "Claves únicas de municipio",
            "ok": len(claves) == 60,
            "detalle": len(claves),
        }
    )

    if len(claves) != 60:
        resultado["apto"] = False
        resultado["errores"].append(
            "Las claves de municipio "
            "no son únicas."
        )

    return resultado

def revisar_seccion(raiz_bged):
    resultado = {
        "capa": "seccion",
        "apto": True,
        "comprobaciones": [],
        "errores": [],
    }

    try:
        shape = ruta_capa(
            raiz_bged,
            "seccion",
        )
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            str(exc)
        )
        return resultado

    base = shape.with_suffix("")

    archivos = {
        ".shp": base.with_suffix(".shp"),
        ".shx": base.with_suffix(".shx"),
        ".dbf": base.with_suffix(".dbf"),
        ".prj": base.with_suffix(".prj"),
    }

    for extension, ruta in archivos.items():
        existe = ruta.exists()

        resultado[
            "comprobaciones"
        ].append(
            {
                "prueba":
                    f"Archivo {extension}",
                "ok": existe,
                "detalle": str(ruta),
            }
        )

        if not existe:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Falta el archivo requerido: "
                f"{ruta}"
            )

    if not resultado["apto"]:
        return resultado

    try:
        ds = DataSource(str(shape))
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir "
            f"el shapefile: {exc}"
        )
        return resultado

    if len(ds) != 1:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba una capa y "
            f"se encontraron {len(ds)}."
        )
        return resultado

    layer = ds[0]

    cantidad = len(layer)

    resultado[
        "comprobaciones"
    ].append(
        {
            "prueba":
                "Cantidad de registros",
            "ok": cantidad > 0,
            "detalle": cantidad,
        }
    )

    campos = set(layer.fields)

    requeridos = CAPAS[
        "seccion"
    ]["campos_obligatorios"]

    faltantes = (
        requeridos - campos
    )

    resultado[
        "comprobaciones"
    ].append(
        {
            "prueba":
                "Campos obligatorios",
            "ok": not faltantes,
            "detalle": sorted(campos),
        }
    )

    if faltantes:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Faltan campos obligatorios: "
            f"{', '.join(sorted(faltantes))}"
        )

    srid = (
        layer.srs.srid
        if layer.srs
        else None
    )

    resultado[
        "comprobaciones"
    ].append(
        {
            "prueba": "SRID",
            "ok": srid == 32614,
            "detalle": srid,
        }
    )

    if srid != 32614:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba EPSG:32614 "
            f"y se encontró {srid}."
        )

    claves = set()
    duplicadas = set()

    for feature in layer:
        entidad = int(
            feature.get("entidad")
        )

        distrito = int(
            feature.get("distrito")
        )

        distrito_local = int(
            feature.get("distrito_l")
        )

        municipio = int(
            feature.get("municipio")
        )

        seccion = int(
            feature.get("seccion")
        )

        if seccion in claves:
            duplicadas.add(
                seccion
            )

        claves.add(
            seccion
        )

        if entidad != ENTIDAD_INE:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Sección {seccion:04}: "
                f"entidad {entidad}."
            )

        if not Distrito.objects.filter(
            distrito=distrito
        ).exists():
            resultado["apto"] = False
            resultado["errores"].append(
                f"Sección {seccion:04}: "
                f"distrito federal "
                f"{distrito:02} inexistente."
            )

        if not DistritoLocal.objects.filter(
            distrito_local=distrito_local
        ).exists():
            resultado["apto"] = False
            resultado["errores"].append(
                f"Sección {seccion:04}: "
                f"distrito local "
                f"{distrito_local:02} "
                "inexistente."
            )

        if not Municipio.objects.filter(
            municipio=municipio
        ).exists():
            resultado["apto"] = False
            resultado["errores"].append(
                f"Sección {seccion:04}: "
                f"municipio "
                f"{municipio:03} "
                "inexistente."
            )

        geom = feature.geom.geos
        geom.srid = 32614

        if geom.geom_type not in (
            "Polygon",
            "MultiPolygon",
        ):
            resultado["apto"] = False
            resultado["errores"].append(
                f"Sección {seccion:04}: "
                f"geometría inesperada "
                f"{geom.geom_type}."
            )

        if not geom.valid:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Sección {seccion:04}: "
                "geometría inválida."
            )

    resultado[
        "comprobaciones"
    ].append(
        {
            "prueba":
                "Claves únicas de sección",
            "ok": not duplicadas,
            "detalle": (
                len(claves)
                if not duplicadas
                else sorted(duplicadas)
            ),
        }
    )

    if duplicadas:
        resultado["apto"] = False
        resultado["errores"].append(
            "Existen claves de sección "
            f"duplicadas: "
            f"{sorted(duplicadas)}"
        )

    return resultado

def revisar_localidad(raiz_bged):
    resultado = {
        "capa": "localidad",
        "apto": True,
        "comprobaciones": [],
        "errores": [],
    }

    shape = ruta_capa(
        raiz_bged,
        "localidad",
    )

    base = shape.with_suffix("")

    archivos = {
        ".shp": base.with_suffix(".shp"),
        ".shx": base.with_suffix(".shx"),
        ".dbf": base.with_suffix(".dbf"),
        ".prj": base.with_suffix(".prj"),
    }

    # ---------------------------------
    # ARCHIVOS
    # ---------------------------------

    for extension, ruta in archivos.items():
        existe = ruta.exists()

        resultado["comprobaciones"].append(
            {
                "prueba": f"Archivo {extension}",
                "ok": existe,
                "detalle": str(ruta),
            }
        )

        if not existe:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Falta el archivo requerido: {ruta}"
            )

    if not resultado["apto"]:
        return resultado

    # ---------------------------------
    # ABRIR CAPA
    # ---------------------------------

    try:
        ds = DataSource(str(shape))
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir el shapefile: {exc}"
        )
        return resultado

    if len(ds) != 1:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba una capa y se encontraron {len(ds)}."
        )
        return resultado

    layer = ds[0]

    # ---------------------------------
    # CANTIDAD
    # ---------------------------------

    cantidad = len(layer)

    resultado["comprobaciones"].append(
        {
            "prueba": "Cantidad de registros",
            "ok": cantidad > 0,
            "detalle": cantidad,
        }
    )

    if cantidad == 0:
        resultado["apto"] = False
        resultado["errores"].append(
            "La capa de localidad no contiene registros."
        )

    # ---------------------------------
    # CAMPOS OBLIGATORIOS
    # ---------------------------------

    campos = set(layer.fields)

    requeridos = CAPAS[
        "localidad"
    ]["campos_obligatorios"]

    faltantes = requeridos - campos

    resultado["comprobaciones"].append(
        {
            "prueba": "Campos obligatorios",
            "ok": not faltantes,
            "detalle": sorted(campos),
        }
    )

    if faltantes:
        resultado["apto"] = False
        resultado["errores"].append(
            "Faltan campos obligatorios: "
            + ", ".join(sorted(faltantes))
        )

    # ---------------------------------
    # SRID
    # ---------------------------------

    srid = (
        layer.srs.srid
        if layer.srs
        else None
    )

    resultado["comprobaciones"].append(
        {
            "prueba": "SRID",
            "ok": srid == 32614,
            "detalle": srid,
        }
    )

    if srid != 32614:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba EPSG:32614 y se encontró {srid}."
        )

    # ---------------------------------
    # SECCIONES DE LA MISMA BGD
    # ---------------------------------

    shape_seccion = ruta_capa(
        raiz_bged,
        "seccion",
    )

    try:
        ds_seccion = DataSource(
            str(shape_seccion)
        )
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir la capa de sección: {exc}"
        )
        return resultado

    layer_seccion = ds_seccion[0]

    secciones_bgd = {
        int(feature.get("seccion"))
        for feature in layer_seccion
    }

    # ---------------------------------
    # VALIDAR REGISTROS
    # ---------------------------------

    claves = set()
    duplicadas = set()
    secciones_inexistentes = set()
    entidades_invalidas = set()
    geometrias_invalidas = 0

    for feature in layer:
        entidad = int(
            feature.get("entidad")
        )

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

        if clave in claves:
            duplicadas.add(clave)

        claves.add(clave)

        if entidad != ENTIDAD_INE:
            entidades_invalidas.add(
                entidad
            )

        if seccion_id not in secciones_bgd:
            secciones_inexistentes.add(
                seccion_id
            )

        geom = feature.geom.geos
        geom.srid = 32614

        if (
            geom.geom_type != "Point"
            or not geom.valid
        ):
            geometrias_invalidas += 1

    # ---------------------------------
    # CLAVES ÚNICAS
    # ---------------------------------

    resultado["comprobaciones"].append(
        {
            "prueba": "Claves únicas de localidad",
            "ok": not duplicadas,
            "detalle": len(claves),
        }
    )

    if duplicadas:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Existen {len(duplicadas)} "
            "claves de localidad duplicadas."
        )

    # ---------------------------------
    # ENTIDAD
    # ---------------------------------

    resultado["comprobaciones"].append(
        {
            "prueba": "Clave de entidad",
            "ok": not entidades_invalidas,
            "detalle": (
                ENTIDAD_INE
                if not entidades_invalidas
                else sorted(entidades_invalidas)
            ),
        }
    )

    if entidades_invalidas:
        resultado["apto"] = False
        resultado["errores"].append(
            "Hay localidades asociadas a "
            "una entidad diferente de "
            f"{ENTIDAD_INE}."
        )

    # ---------------------------------
    # SECCIONES EXISTENTES
    # ---------------------------------

    resultado["comprobaciones"].append(
        {
            "prueba": "Secciones existentes",
            "ok": not secciones_inexistentes,
            "detalle": (
                "OK"
                if not secciones_inexistentes
                else sorted(secciones_inexistentes)
            ),
        }
    )

    if secciones_inexistentes:
        resultado["apto"] = False
        resultado["errores"].append(
            "Hay localidades asociadas a "
            "secciones inexistentes en seccion.shp."
        )

    # ---------------------------------
    # GEOMETRÍAS
    # ---------------------------------

    resultado["comprobaciones"].append(
        {
            "prueba": "Geometrías Point válidas",
            "ok": geometrias_invalidas == 0,
            "detalle": geometrias_invalidas,
        }
    )

    if geometrias_invalidas:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se encontraron {geometrias_invalidas} "
            "geometrías de localidad inválidas "
            "o distintas de Point."
        )

    return resultado

def revisar_manzana(raiz_bged):
    resultado = {
        "capa": "manzana",
        "apto": True,
        "comprobaciones": [],
        "errores": [],
    }

    shape = ruta_capa(
        raiz_bged,
        "manzana",
    )

    base = shape.with_suffix("")

    archivos = {
        ".shp": base.with_suffix(".shp"),
        ".shx": base.with_suffix(".shx"),
        ".dbf": base.with_suffix(".dbf"),
        ".prj": base.with_suffix(".prj"),
    }

    # ---------------------------------
    # ARCHIVOS
    # ---------------------------------

    for extension, ruta in archivos.items():
        existe = ruta.exists()

        resultado["comprobaciones"].append(
            {
                "prueba": f"Archivo {extension}",
                "ok": existe,
                "detalle": str(ruta),
            }
        )

        if not existe:
            resultado["apto"] = False
            resultado["errores"].append(
                f"Falta el archivo requerido: {ruta}"
            )

    if not resultado["apto"]:
        return resultado

    # ---------------------------------
    # ABRIR CAPA
    # ---------------------------------

    try:
        ds = DataSource(str(shape))
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir el shapefile: {exc}"
        )
        return resultado

    if len(ds) != 1:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba una capa y se encontraron {len(ds)}."
        )
        return resultado

    layer = ds[0]

    # ---------------------------------
    # CANTIDAD
    # ---------------------------------

    cantidad = len(layer)

    resultado["comprobaciones"].append(
        {
            "prueba": "Cantidad de registros",
            "ok": cantidad > 0,
            "detalle": cantidad,
        }
    )

    if cantidad == 0:
        resultado["apto"] = False
        resultado["errores"].append(
            "La capa de manzana no contiene registros."
        )

    # ---------------------------------
    # CAMPOS OBLIGATORIOS
    # ---------------------------------

    campos = set(layer.fields)

    requeridos = CAPAS[
        "manzana"
    ]["campos_obligatorios"]

    faltantes = requeridos - campos

    resultado["comprobaciones"].append(
        {
            "prueba": "Campos obligatorios",
            "ok": not faltantes,
            "detalle": sorted(campos),
        }
    )

    if faltantes:
        resultado["apto"] = False
        resultado["errores"].append(
            "Faltan campos obligatorios: "
            + ", ".join(sorted(faltantes))
        )

    # ---------------------------------
    # SRID
    # ---------------------------------

    srid = (
        layer.srs.srid
        if layer.srs
        else None
    )

    resultado["comprobaciones"].append(
        {
            "prueba": "SRID",
            "ok": srid == 32614,
            "detalle": srid,
        }
    )

    if srid != 32614:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se esperaba EPSG:32614 y se encontró {srid}."
        )

    # ---------------------------------
    # SECCIONES DE LA MISMA BGD
    # ---------------------------------

    shape_seccion = ruta_capa(
        raiz_bged,
        "seccion",
    )

    try:
        ds_seccion = DataSource(
            str(shape_seccion)
        )
    except Exception as exc:
        resultado["apto"] = False
        resultado["errores"].append(
            f"No fue posible abrir la capa de sección: {exc}"
        )
        return resultado

    layer_seccion = ds_seccion[0]

    secciones_bgd = {
        int(feature.get("seccion"))
        for feature in layer_seccion
    }

    # ---------------------------------
    # VALIDAR REGISTROS
    #
    # La BGD es la fuente de verdad.
    # Para Manzana solo se comprueba que
    # la sección referida exista en la
    # capa Sección de la misma BGD.
    # ---------------------------------

    claves = set()
    duplicadas = set()
    secciones_inexistentes = set()
    geometrias_invalidas = 0

    for feature in layer:
        seccion_id = int(
            feature.get("seccion")
        )

        localidad = int(
            feature.get("localidad")
        )

        manzana = int(
            feature.get("manzana")
        )

        clave = (
            seccion_id,
            localidad,
            manzana,
        )

        if clave in claves:
            duplicadas.add(clave)

        claves.add(clave)

        if seccion_id not in secciones_bgd:
            secciones_inexistentes.add(
                seccion_id
            )

        geom = feature.geom.geos
        geom.srid = 32614

        if (
            geom.geom_type not in (
                "Polygon",
                "MultiPolygon",
            )
            or not geom.valid
        ):
            geometrias_invalidas += 1

    # ---------------------------------
    # CLAVES ÚNICAS
    # ---------------------------------

    resultado["comprobaciones"].append(
        {
            "prueba": "Claves únicas de manzana",
            "ok": not duplicadas,
            "detalle": len(claves),
        }
    )

    if duplicadas:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Existen {len(duplicadas)} "
            "claves de manzana duplicadas."
        )

    # ---------------------------------
    # SECCIONES EXISTENTES
    # ---------------------------------

    resultado["comprobaciones"].append(
        {
            "prueba": "Secciones existentes",
            "ok": not secciones_inexistentes,
            "detalle": (
                "OK"
                if not secciones_inexistentes
                else sorted(secciones_inexistentes)
            ),
        }
    )

    if secciones_inexistentes:
        resultado["apto"] = False
        resultado["errores"].append(
            "Hay manzanas asociadas a "
            "secciones inexistentes en seccion.shp."
        )

    # ---------------------------------
    # GEOMETRÍAS
    # ---------------------------------

    resultado["comprobaciones"].append(
        {
            "prueba": "Geometrías válidas",
            "ok": geometrias_invalidas == 0,
            "detalle": geometrias_invalidas,
        }
    )

    if geometrias_invalidas:
        resultado["apto"] = False
        resultado["errores"].append(
            f"Se encontraron {geometrias_invalidas} "
            "geometrías inválidas."
        )

    return resultado
