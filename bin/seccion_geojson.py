import os
import sys
import json
from pathlib import Path
import django

BASE_PATH = Path(__file__).resolve().parent.parent
SRC_PATH = BASE_PATH / "src"

sys.path.append(str(SRC_PATH))

if os.name == "nt":
    QGIS_BIN = r'C:\Program Files\QGIS 3.28.12\bin'
    os.environ['PATH'] = f"{QGIS_BIN};{os.environ.get('PATH', '')}"

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.gis.geos import GEOSGeometry
from apps.pusinex.models import Seccion

SHAPES = BASE_PATH / "data" / "shapes"

with open(SHAPES / "seccion.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

for feature in data["features"]:
    propiedades = feature["properties"]
    geometria = GEOSGeometry(json.dumps(feature["geometry"]))

    geometria.srid = 32614

    Seccion.objects.update_or_create(
        seccion=propiedades["seccion"],
        defaults={
            "entidad_id": propiedades["entidad"],
            "distrito_id": propiedades["distrito"],
            "distrito_l_id": propiedades["distrito_l"],
            "municipio_id": propiedades["municipio"],
            "tipo": propiedades["tipo"],
            "geom": geometria,
        },
    )
