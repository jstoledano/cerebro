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
}


def ruta_capa(raiz_bged, capa):
    raiz = Path(raiz_bged)
    config = CAPAS[capa]

    return (
        raiz
        / str(ENTIDAD_INE)
        / config["carpeta"]
        / config["archivo"]
    )
