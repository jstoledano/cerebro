from pathlib import Path

from django.contrib.gis.gdal import DataSource

from .registry import CAPAS, ENTIDAD_INE, ruta_capa


class DoctorError(Exception):
    pass


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
