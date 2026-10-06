from django.urls import path
from django.views.generic import RedirectView

from apps.pusinex.views import (
    Administration,
    CreatePUSINEX,
    DistrictPUSINEXPackageDownload,
    DistritoDetail,
    Index,
    MunicipioDetail,
    PUSINEXLastUpdate,
    GeneratePUSINEXPackages,
    PusinexDetail,
    SeccionDetail,
    StatePUSINEXPackageDownload,
    VNM2026Cobertura,
    VNM2026Index,
    VNM2026PackageDownload,
)

app_name = "pusinex"

urlpatterns = [
    path(
        "vnm2026/",
        VNM2026Index.as_view(),
        name="vnm2026",
    ),
    path(
        "vnm2026/cobertura/",
        VNM2026Cobertura.as_view(),
        name="vnm2026_cobertura",
    ),
    path(
        "vnm2026/distrito/<int:district>/descargar/",
        VNM2026PackageDownload.as_view(),
        name="vnm2026_package",
    ),
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
        GeneratePUSINEXPackages.as_view(),
        name="generate_packages",
    ),
    # Descargas publicas de paquetes previamente generados.
    path(
        "paquetes/estatal/",
        StatePUSINEXPackageDownload.as_view(),
        name="state_package",
    ),
    path(
        "paquetes/distrito/<int:pk>/",
        DistrictPUSINEXPackageDownload.as_view(),
        name="district_package",
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
            pattern_name="pusinex:state_package",
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
            pattern_name="pusinex:state_package",
            permanent=False,
        ),
        name="package_legacy",
    ),
    path("", Index.as_view(), name="index"),
]
