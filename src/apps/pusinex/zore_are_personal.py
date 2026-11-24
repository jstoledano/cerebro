"""Expedientes de personal ZORE/ARE, con vista demostrativa segura.

La demostracion se construye en memoria y nunca persiste nombres o contactos.
El acceso a datos reales requiere pusinex.ver_personal_zore_are.
"""
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .zore_models import Are, SeccionAre, Zore
from .zore_are_views import _datos


_NOMBRES_SE = (
    "Mariana Ejemplo Torres", "Rafael Ejemplo Luna", "Sofía Ejemplo Ramos",
    "Emilio Ejemplo Serrano", "Valeria Ejemplo Paredes", "Andrés Ejemplo Salas",
)
_NOMBRES_CAE = (
    "Daniela Ejemplo Castro", "Héctor Ejemplo Ríos", "Carolina Ejemplo Peña",
    "Ignacio Ejemplo Lara", "Paola Ejemplo Vega", "Luis Ejemplo Ortiz",
)


def _simulado(tipo, grupo):
    """Datos ficticios; contactos .invalid y telefono inutilizable."""
    es_se = tipo == "supervisor"
    nombres = _NOMBRES_SE if es_se else _NOMBRES_CAE
    ordinal = (grupo.distrito_id * 1000 + grupo.numero)
    nombre = nombres[ordinal % len(nombres)]
    etiqueta = "SE" if es_se else "CAE"
    return {
        "nombre": nombre,
        "correo": f"{etiqueta.lower()}.demo.d{grupo.distrito_id:02d}.{grupo.numero:03d}@example.invalid",
        "telefono": "000 000 0000",
        "identificador": f"DEMO-{etiqueta}-{grupo.distrito_id:02d}-{grupo.numero:03d}",
        "cargo": "Supervisor/a Electoral" if es_se else "Capacitador/a-Asistente Electoral",
        "demostracion": True,
    }


def _reales(tipo, grupo):
    es_se = tipo == "supervisor"
    return {
        "nombre": grupo.supervisor_nombre if es_se else grupo.cae_nombre,
        "correo": grupo.supervisor_correo if es_se else grupo.cae_correo,
        "telefono": grupo.supervisor_telefono if es_se else grupo.cae_telefono,
        "identificador": "",
        "cargo": "Supervisor/a Electoral" if es_se else "Capacitador/a-Asistente Electoral",
        "demostracion": False,
    }


def _expediente(request, tipo, pk):
    es_se = tipo == "supervisor"
    grupo = get_object_or_404(Zore if es_se else Are, pk=pk)
    puede_ver_personal = (
        request.user.is_authenticated and
        request.user.has_perm("pusinex.ver_personal_zore_are")
    )
    # Solo '1' activa el modo demostrativo. Esta informacion es sintetica.
    demo = request.GET.get("demo") == "1"
    personal = _simulado(tipo, grupo) if demo else (
        _reales(tipo, grupo) if puede_ver_personal else None
    )
    datos = _datos("zore" if es_se else "are", grupo.pk)
    if es_se:
        zona = next((z for z in datos["zores"] if z["id"] == grupo.pk), None)
        metrics = [
            ("ARE bajo supervisión", len(zona["areas"]) if zona else 0),
            ("Secciones electorales", zona["secciones"] if zona else 0),
            ("Lista nominal de secciones", zona["lista_nominal"] if zona else 0),
        ]
        referencias = [
            {"label": f"ARE {a.numero:03d}", "url": reverse("pusinex:are", args=[a.pk])}
            for a in grupo.ares.order_by("numero")
        ]
        padre = {"label": f"ZORE {grupo.numero:02d}", "url": reverse("pusinex:zore", args=[grupo.pk])}
    else:
        area = next((a for a in datos["ares"] if a["id"] == grupo.pk), None)
        metrics = [
            ("Secciones asignadas", area["secciones"] if area else 0),
            ("Casillas LN asignadas", area["casillas_ln"] if area else None),
            ("Lista nominal estimada", area["ln_estimada"] if area else None),
        ]
        referencias = [
            {"label": f"Sección {s['numero']:04d}", "url": s["url"]}
            for s in datos["secciones"]
        ]
        padre = {"label": f"ARE {grupo.numero:03d}", "url": reverse("pusinex:are", args=[grupo.pk])}
    return render(request, "pusinex/zore_are_personal_detail.html", {
        "tipo_personal": tipo,
        "grupo": grupo,
        "personal": personal,
        "demo": demo,
        "autorizado": puede_ver_personal,
        "metricas": metrics,
        "referencias": referencias,
        "padre": padre,
        "distrito": grupo.distrito_id,
        "grupo_zore": grupo if es_se else grupo.zore,
        "carto_basemaps_api_key": settings.CARTO_BASEMAPS_API_KEY,
    })


def supervisor_detail(request, pk):
    return _expediente(request, "supervisor", pk)


def cae_detail(request, pk):
    return _expediente(request, "cae", pk)
