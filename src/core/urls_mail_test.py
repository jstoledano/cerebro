from django.http import HttpResponse
from django.urls import include, path
from apps.pas.notification_views import agenda_correo, calendario_correo


def placeholder(request, **kwargs):
    return HttpResponse("Ruta auxiliar de las pruebas de notificaciones.")


def group(namespace, names):
    return path(f"{namespace}/", include(([
        path(f"{name}/", placeholder, name=name) for name in names
    ], namespace)))


urlpatterns = [
    path("", placeholder, name="index"),
    path("login/", placeholder, name="login"),
    path("logout/", placeholder, name="logout"),
    path("pas/", include(([
        path("", placeholder, name="index"),
        path("agenda/", placeholder, name="agenda"),
        path("agenda/correo/", agenda_correo, name="agenda-correo"),
        path("agenda/calendario-correo/", calendario_correo, name="calendario-correo"),
        path("executions/<int:pk>/evidence/", placeholder, name="execution-evidence"),
    ], "pas"))),
    path("docs/", include(([
        path("", placeholder, name="index"),
        path("buscador/", placeholder, name="buscador"),
        path("movil/", placeholder, name="cmi_movil_help"),
        path("<int:pk>/", placeholder, name="detalle"),
    ], "docs"))),
    group("cecyrd", ["index"]), group("art141", ["dashboard"]), group("ideas", ["index"]),
    group("pmml", ["register"]),
    group("pusinex", ["index", "administration", "vnm2026_cobertura", "vnm2026_actualizacion"]),
]
