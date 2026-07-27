from django.urls import path
from django.views.generic import RedirectView

from apps.pusinex.views import (
    VNM2024,
    Administration,
    CreatePUSINEX,
    DistritoDetail,
    Index,
    MunicipioDetail,
    PUSINEXLastUpdate,
    PUSINEXZip,
    PusinexDetail,
    SeccionDetail,
    VNMZipView,
)

app_name = "pusinex"

urlpatterns = [
    path("vnm/", VNM2024.as_view(), name="vnm"),
    path("vnm/<int:dto>", VNMZipView.as_view(), name="vnmZip"),
    path("pusinex/<int:pk>", PusinexDetail.as_view(), name="pusinex"),
    path("seccion/<int:pk>", SeccionDetail.as_view(), name="seccion"),
    path("municipio/<int:pk>", MunicipioDetail.as_view(), name="municipio"),
    path("distrito/<int:pk>", DistritoDetail.as_view(), name="distrito"),
    path("latest/", PUSINEXLastUpdate.as_view(), name="latest"),

    # Rutas canonicas de gestion.
    path("gestion/", Administration.as_view(), name="administration"),
    path("gestion/subir/", CreatePUSINEX.as_view(), name="create"),
    path(
        "gestion/generar-paquetes/",
        PUSINEXZip.as_view(),
        name="generate_packages",
    ),

    # Compatibilidad temporal con enlaces anteriores.
    path(
        "bgd/",
        RedirectView.as_view(
            pattern_name="pusinex:administration",
            permanent=False,
        ),
        name="bgd",
    ),
    path(
        "creation/",
        RedirectView.as_view(
            pattern_name="pusinex:create",
            permanent=False,
        ),
        name="creation_legacy",
    ),
    path(
        "paquete/",
        RedirectView.as_view(
            pattern_name="pusinex:generate_packages",
            permanent=False,
        ),
        name="paquete",
    ),
    path(
        "gestion/nuevo/",
        RedirectView.as_view(
            pattern_name="pusinex:create",
            permanent=False,
        ),
        name="create_legacy",
    ),
    path(
        "gestion/descargar-paquete/",
        RedirectView.as_view(
            pattern_name="pusinex:generate_packages",
            permanent=False,
        ),
        name="package_legacy",
    ),
    path("", Index.as_view(), name="index"),
]
