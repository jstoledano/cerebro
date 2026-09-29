import os
import sys
import json
from pathlib import Path
import django

BASE_PATH = Path(__file__).resolve().parent.parent
SRC_PATH = BASE_PATH / "src"

sys.path.append(str(SRC_PATH))



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.gis.geos import GEOSGeometry
from apps.pusinex.models import DistritoLocal

SHAPES = BASE_PATH / "data" / "shapes"

with open(SHAPES / "distrito_local.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

for feature in data["features"]:
    propiedades = feature["properties"]
    geometria = GEOSGeometry(json.dumps(feature["geometry"]))

    geometria.srid = 32614

    DistritoLocal.objects.update_or_create(
        distrito_local=propiedades["distrito_local"],
        defaults={
            "entidad_id": propiedades["entidad"],
            "cabecera": "",
            "geom": geometria,
        },
    )
