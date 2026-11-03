from django.http import HttpResponseNotFound
from django.urls import include, path

from core.views import Index


def modulo_fuera_de_prueba(request, *args, **kwargs):
    return HttpResponseNotFound(
        "Este módulo está fuera de esta configuración de pruebas."
    )


def rutas_auxiliares(namespace, nombres):
    return include(
        (
            [
                path(
                    f"{nombre}/",
                    modulo_fuera_de_prueba,
                    name=nombre,
                )
                for nombre in nombres
            ],
            namespace,
        ),
        namespace=namespace,
    )


urlpatterns = [
    path("pas/", include("apps.pas.urls")),
    path("profiles/", include("apps.profiles.urls")),
    path("api/v1/pas/", include("apps.pas.api.urls")),
    path("", Index.as_view(), name="index"),

    # Enlaces del diseño compartido, disponibles solo para resolver URLs.
    path("login/", modulo_fuera_de_prueba, name="login"),
    path("logout/", modulo_fuera_de_prueba, name="logout"),
    path(
        "cecyrd/",
        rutas_auxiliares("cecyrd", ["index"]),
    ),
    path(
        "art141/",
        rutas_auxiliares("art141", ["dashboard"]),
    ),
    path(
        "docs/",
        rutas_auxiliares(
            "docs",
            ["index", "cmi_movil_help", "buscador"],
        ),
    ),
    path(
        "pmml/",
        rutas_auxiliares("pmml", ["register"]),
    ),
    path(
        "cartografia/",
        rutas_auxiliares(
            "pusinex",
            [
                "index",
                "vnm2026_cobertura",
                "vnm2026_actualizacion",
                "administration",
            ],
        ),
    ),
    path(
        "ideas/",
        rutas_auxiliares("ideas", ["index"]),
    ),
]
