import os
import sys
import json
from pathlib import Path
import django

distrito = {
    "modelo": "Distrito",
    "file": "distrito.geojson",
    "pk": "distrito",
    "campos": ["entidad", "tipo"]
}

distrito_local = {
    "modelo": "DistritoLocal",
    "file": "distrito_local.geojson",
    "pk": "distrito_local",
    "campos": ["entidad"]
}


BASE_PATH = Path(__file__).resolve().parent.parent
SRC_PATH = BASE_PATH / "src"

sys.path.append(str(SRC_PATH))

if os.name == "nt":
    QGIS_BIN = r'C:\Program Files\QGIS 3.28.12\bin'
    os.environ['PATH'] = f"{QGIS_BIN};{os.environ.get('PATH', '')}"

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.gis.geos import GEOSGeometry
from apps.pusinex.models import Entidad

SHAPES = BASE_PATH / "data" / "shapes"

with open(SHAPES / "entidad.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

for feature in data["features"]:
    propiedades = feature["properties"]
    geometria = GEOSGeometry(json.dumps(feature["geometry"]))

    geometria.srid = 32614

    Entidad.objects.update_or_create(
        entidad=propiedades["entidad"],
        defaults={
            "nombre": propiedades["nombre"],
            "circunscripcion": propiedades["circunscripcion"],
            "geom": geometria,
        },
    )
