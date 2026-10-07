import re
from pathlib import Path


ENTIDAD_INE = 29


CAPAS = {
    "entidad": {
        "carpeta": "entidad",
        "archivo": "entidad.shp",
        "campos_obligatorios": {
            "entidad",
            "nombre",
        },
        "campos_opcionales": {
            "circunscri",
        },
    },

    "distrito": {
        "carpeta": "distrito",
        "archivo": "distrito.shp",
        "campos_obligatorios": {
            "entidad",
            "distrito",
            "tipo",
        },
        "campos_opcionales": set(),
    },

    "distrito_local": {
        "carpeta": "distrito_local",
        "archivo": "distrito_local.shp",
        "campos_obligatorios": {
            "entidad",
            "distrito_l",
        },
        "campos_opcionales": set(),
    },

    "municipio": {
        "carpeta": "municipio",
        "archivo": "municipio.shp",
        "campos_obligatorios": {
            "entidad",
            "municipio",
            "nombre",
        },
        "campos_opcionales": set(),
    },

    "seccion": {
        "archivo": "seccion.shp",
        "campos_obligatorios": {
            "entidad",
            "distrito",
            "distrito_l",
            "municipio",
            "seccion",
            "tipo",
        },
        "campos_opcionales": set(),
    },
    "localidad": {
        "carpeta": "localidad",
        "archivo": "localidad.shp",
        "campos_obligatorios": {
            "entidad",
            "distrito",
            "distrito_l",
            "municipio",
            "seccion",
            "localidad",
            "nombre",
            "tipo",
            "cabecera",
            "status",
            "control",
            "id",
        },
        "campos_opcionales": set(),
    },
    "manzana": {
        "carpeta": "manzana",
        "archivo": "manzana.shp",
        "campos_obligatorios": {
            "entidad",
            "distrito",
            "municipio",
            "seccion",
            "localidad",
            "manzana",
            "distrito_l",
        },
        "campos_opcionales": {
            "status",
            "control",
            "caso_captu",
            "disperso",
            "id",
            "tipo_manza",
        },
    },
}


def _ruta_seccion(raiz_entidad):
    candidatos = []

    patron = re.compile(
        r"^seccion(?:_(\d+))?$"
    )

    for ruta in raiz_entidad.iterdir():
        if not ruta.is_dir():
            continue

        match = patron.match(ruta.name)

        if not match:
            continue

        shape = ruta / "seccion.shp"

        if shape.exists():
            numero = match.group(1)

            prioridad = (
                0
                if numero is None
                else int(numero)
            )

            candidatos.append(
                (prioridad, ruta)
            )

    if not candidatos:
        raise FileNotFoundError(
            "No se encontró un directorio de sección "
            "válido. Se esperaba 'seccion' o "
            "'seccion_<n>' con seccion.shp."
        )

    candidatos.sort(
        key=lambda item: item[0]
    )

    carpeta = candidatos[0][1]

    return carpeta / "seccion.shp"


def ruta_capa(raiz_bged, capa):
    raiz = Path(raiz_bged)

    raiz_entidad = (
        raiz
        / str(ENTIDAD_INE)
    )

    if capa == "seccion":
        return _ruta_seccion(
            raiz_entidad
        )

    config = CAPAS[capa]

    return (
        raiz_entidad
        / config["carpeta"]
        / config["archivo"]
    )
