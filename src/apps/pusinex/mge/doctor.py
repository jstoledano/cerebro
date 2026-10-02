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
