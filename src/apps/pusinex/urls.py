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
    VNM2026ActualizacionPackageDownload,
    VNM2026CoberturaPackageDownload,
    VNM2026Actualizacion,
    VNM2026Cobertura,
    VNM2026Index,
)

from .zore_are_views import ZoreDetail, AreDetail, asignaciones_geojson
from .zore_are_personal import supervisor_detail, cae_detail

from .distrito_local_views import DistritoLocalDetail
from .zore_are_views import colindancias_geojson

app_name = "pusinex"

urlpatterns = [
    path("distrito-local/<int:pk>", DistritoLocalDetail.as_view(), name="distrito_local"),
    path("zore-are/colindancias/", colindancias_geojson, name="zore_are_colindancias"),
    path("zore-are/datos/", asignaciones_geojson, name="zore_are_api"),
    path("zore/<int:pk>", ZoreDetail.as_view(), name="zore"),
    path("zore/<int:pk>/supervisor/", supervisor_detail, name="zore_supervisor"),
    path("are/<int:pk>/cae/", cae_detail, name="are_cae"),
    path("are/<int:pk>", AreDetail.as_view(), name="are"),
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
        "vnm2026/actualizacion/",
        VNM2026Actualizacion.as_view(),
        name="vnm2026_actualizacion",
    ),
    path(
        "vnm2026/cobertura/distrito/<int:district>/descargar/",
        VNM2026CoberturaPackageDownload.as_view(),
        name="vnm2026_cobertura_package",
    ),
    path(
        "vnm2026/actualizacion/distrito/<int:district>/descargar/",
        VNM2026ActualizacionPackageDownload.as_view(),
        name="vnm2026_actualizacion_package",
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
