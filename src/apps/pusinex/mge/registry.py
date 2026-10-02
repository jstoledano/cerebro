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
