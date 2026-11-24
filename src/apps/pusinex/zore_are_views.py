"""Vistas informativas y GeoJSON para ZORE y ARE.

No contiene campos de personal en el endpoint JSON. La capa cartografica
utiliza exclusivamente poligonos de Seccion ya registrados en el MGE.
"""
import json
from collections import defaultdict

from django.conf import settings
from django.core.serializers import serialize
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.generic import DetailView

from .models import Distrito, DistritoLocal, Municipio, Seccion
from .zore_models import Are, SeccionAre, Zore


class ZoreDetail(DetailView):
    model = Zore
    context_object_name = "grupo"
    template_name = "pusinex/zore_are_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "tipo_grupo": "zore",
            "carto_basemaps_api_key": settings.CARTO_BASEMAPS_API_KEY,
            "ver_personal": self.request.user.is_authenticated
            and self.request.user.has_perm("pusinex.ver_personal_zore_are"),
        })
        return context


class AreDetail(DetailView):
    model = Are
    context_object_name = "grupo"
    template_name = "pusinex/zore_are_detail.html"

    def get_queryset(self):
        return super().get_queryset().select_related("zore", "distrito")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "tipo_grupo": "are",
            "carto_basemaps_api_key": settings.CARTO_BASEMAPS_API_KEY,
            "ver_personal": self.request.user.is_authenticated
            and self.request.user.has_perm("pusinex.ver_personal_zore_are"),
        })
        return context


def reparto_ln(total, relaciones, capacidad=750):
    """LN estimada: ARE en orden ascendente, casillas hasta su capacidad.

    Para una seccion compartida, llena primero las casillas asignadas a la
    ARE de menor numero y deja el remanente a la siguiente. Es una convencion
    informativa, no una distribucion nominal efectiva. Si la capacidad total
    resulta insuficiente, no presenta una estimacion.
    """
    if len(relaciones) == 1:
        return {relaciones[0].are_id: total}
    ordenadas = sorted(relaciones, key=lambda r: (r.are.numero, r.are_id))
    if any(r.casillas_ln is None or r.casillas_ln < 1 for r in ordenadas):
        return {r.are_id: None for r in relaciones}
    if sum(r.casillas_ln for r in ordenadas) * capacidad < total:
        return {r.are_id: None for r in relaciones}
    restante = total
    resultado = {}
    for relacion in ordenadas:
        asignada = min(restante, relacion.casillas_ln * capacidad)
        resultado[relacion.are_id] = asignada
        restante -= asignada
    return resultado


def _asignaciones(nivel, pk):
    if nivel == "distrito":
        get_object_or_404(Distrito, pk=pk)
        filtro = {"seccion__distrito_id": pk}
    elif nivel == "distrito_local":
        get_object_or_404(DistritoLocal, pk=pk)
        filtro = {"seccion__distrito_l_id": pk}
    elif nivel == "municipio":
        get_object_or_404(Municipio, pk=pk)
        filtro = {"seccion__municipio_id": pk}
    elif nivel == "seccion":
        get_object_or_404(Seccion, pk=pk)
        filtro = {"seccion_id": pk}
    elif nivel == "zore":
        get_object_or_404(Zore, pk=pk)
        filtro = {"are__zore_id": pk}
    elif nivel == "are":
        get_object_or_404(Are, pk=pk)
        filtro = {"are_id": pk}
    else:
        raise Http404("Ambito cartografico no encontrado")
    return list(
        SeccionAre.objects.filter(**filtro, seccion__activa=True)
        .select_related("seccion", "are", "are__zore")
        .order_by("seccion_id", "are__numero")
    )


def _datos(nivel, pk):
    seleccionadas = _asignaciones(nivel, pk)
    sec_ids = {r.seccion_id for r in seleccionadas}
    # Para el expediente ARE recuperamos las asignaciones hermanas de la seccion
    # y calculamos el reparto antes de filtrar a la ARE seleccionada.
    relaciones = defaultdict(list)
    if sec_ids:
        for r in SeccionAre.objects.filter(seccion_id__in=sec_ids).select_related(
            "seccion", "are", "are__zore"
        ).order_by("are__numero"):
            relaciones[r.seccion_id].append(r)

    secciones = {r.seccion_id: r.seccion for r in seleccionadas}
    seleccion_por_seccion = defaultdict(list)
    for r in seleccionadas:
        seleccion_por_seccion[r.seccion_id].append(r)

    zores = {}
    ares = {}
    secciones_datos = []
    for sec_id in sorted(sec_ids):
        sec = secciones[sec_id]
        partes = relaciones[sec_id]
        visibles = seleccion_por_seccion[sec_id]
        zore = partes[0].are.zore
        ln = reparto_ln(sec.ln, partes)
        z = zores.setdefault(zore.pk, {
            "id": zore.pk, "numero": zore.numero,
            "distrito": zore.distrito_id,
            "url": reverse("pusinex:zore", args=[zore.pk]),
            "secciones": 0, "padron": 0, "lista_nominal": 0,
            "areas": {}, "compartidas": 0, "_municipios": {}, "_locales": {},
        })
        z["secciones"] += 1
        z["_municipios"][sec.municipio_id] = z["_municipios"].get(sec.municipio_id, 0) + 1
        z["_locales"][sec.distrito_l_id] = z["_locales"].get(sec.distrito_l_id, 0) + 1
        z["padron"] += sec.pe
        z["lista_nominal"] += sec.ln
        if len(partes) == 2:
            z["compartidas"] += 1
        sec_ares = []
        for r in visibles:
            area = r.are
            item = ares.setdefault(area.pk, {
                "id": area.pk, "numero": area.numero,
                "distrito": area.distrito_id,
                "zore_id": zore.pk,
                "url": reverse("pusinex:are", args=[area.pk]),
                "secciones": 0, "padron_secciones": 0,
                "ln_estimada": 0, "casillas_ln": 0,
                "compartidas": 0, "estimacion_disponible": True,
                "casillas_disponibles": True,
            })
            item["secciones"] += 1
            if len(partes) == 2:
                item["compartidas"] += 1
            # PE integra cada seccion completa, inclusive si esta compartida.
            # Las cifras de distintas ARE no son sumables sin deduplicar seccion.
            item["padron_secciones"] += sec.pe
            if ln[area.pk] is None:
                item["estimacion_disponible"] = False
            else:
                item["ln_estimada"] += ln[area.pk]
            if r.casillas_ln is None:
                item["casillas_disponibles"] = False
            else:
                item["casillas_ln"] += r.casillas_ln
            z["areas"][area.pk] = True
        # Mostrar todas las ARE de la seccion, tambien cuando la consulta
        # se limita a una de ellas; los colores de franjas deben ser completos.
        sec_ares = [{
            "id": r.are_id,
            "numero": r.are.numero,
            "url": reverse("pusinex:are", args=[r.are_id]),
            "casillas_ln": r.casillas_ln,
            "padron_seccion": sec.pe,
            "ln_estimada": ln[r.are_id],
        } for r in partes]
        secciones_datos.append({
            "id": sec_id, "numero": sec.seccion,
            "distrito": sec.distrito_id, "municipio": sec.municipio_id, "distrito_local": sec.distrito_l_id,
            "padron": sec.pe, "lista_nominal": sec.ln,
            "url": reverse("pusinex:seccion", args=[sec_id]),
            "zore": {"id": zore.pk, "numero": zore.numero, "url": z["url"]},
            "ares": sec_ares,
            "compartida": len(partes) == 2,
        })

    # Serializacion unica para evitar transformaciones repetidas de GEOS.
    sec_qs = Seccion.objects.filter(pk__in=sec_ids)
    geojson = json.loads(serialize("geojson", sec_qs, geometry_field="geom", fields=("seccion",)))
    por_id = {s["id"]: s for s in secciones_datos}
    for feature in geojson["features"]:
        sec_id = int(feature["id"])
        if sec_id in por_id:
            feature["properties"] = por_id[sec_id]

    municipio_ids = set().union(*(set(z["_municipios"]) for z in zores.values())) if zores else set()
    local_ids = set().union(*(set(z["_locales"]) for z in zores.values())) if zores else set()
    municipios_ref = {m.pk: m for m in Municipio.objects.filter(pk__in=municipio_ids)}
    locales_ref = {d.pk: d for d in DistritoLocal.objects.filter(pk__in=local_ids)}
    for z in zores.values():
        z["areas"] = sorted(z["areas"])
        z["municipios"] = [
            {"numero": mid, "nombre": municipios_ref[mid].nombre,
             "secciones": cuenta, "url": reverse("pusinex:municipio", args=[mid])}
            for mid, cuenta in sorted(z.pop("_municipios").items()) if mid in municipios_ref
        ]
        z["distritos_locales"] = [
            {"numero": did, "secciones": cuenta,
             "url": reverse("pusinex:distrito_local", args=[did])}
            for did, cuenta in sorted(z.pop("_locales").items()) if did in locales_ref
        ]
    for a in ares.values():
        if not a.pop("estimacion_disponible"):
            a["ln_estimada"] = None
        if not a.pop("casillas_disponibles"):
            a["casillas_ln"] = None

    # Una ARE puede atravesar limites de distritos locales. El diagnostico
    # considera TODAS sus secciones, aun cuando el expediente actual filtre
    # por municipio o distrito local.
    are_ids = {r.are_id for r in seleccionadas}
    locales_por_are = defaultdict(set)
    if are_ids:
        for are_id, local_id in SeccionAre.objects.filter(
            are_id__in=are_ids, seccion__activa=True
        ).values_list("are_id", "seccion__distrito_l_id"):
            locales_por_are[are_id].add(local_id)
    are_por_id = {r.are_id: r.are for r in seleccionadas}
    alertas_multilocal = [
        {
            "are_id": are_id,
            "numero": are_por_id[are_id].numero,
            "distrito": are_por_id[are_id].distrito_id,
            "url": reverse("pusinex:are", args=[are_id]),
            "distritos_locales": sorted(locales),
        }
        for are_id, locales in sorted(locales_por_are.items())
        if len(locales) > 1
    ]

    return {
        "tipo": nivel, "id": pk,
        "alertas_are_multilocal": alertas_multilocal,
        "geojson": geojson,
        "secciones": secciones_datos,
        "zores": sorted(zores.values(), key=lambda z: (z["distrito"], z["numero"])),
        "ares": sorted(ares.values(), key=lambda a: (a["distrito"], a["numero"])),
    }


@require_GET
def asignaciones_geojson(request):
    nivel = request.GET.get("nivel", "").strip().lower()
    try:
        pk = int(request.GET.get("pk", ""))
    except (ValueError, TypeError):
        raise Http404("Identificador invalido")
    if pk < 1:
        raise Http404("Identificador invalido")
    # No se incluyen nombres, correos ni telefonos en el JSON.
    datos = _datos(nivel, pk)
    datos["puede_importar"] = bool(
        nivel == "distrito"
        and request.user.is_authenticated
        and request.user.has_perm("pusinex.change_zore")
    )
    return JsonResponse(datos, json_dumps_params={"ensure_ascii": False})


@require_GET
def colindancias_geojson(request):
    """Vecindad por frontera lineal compartida; sin datos personales.

    La geometria de una ARE es la union visual de secciones completas.
    Las secciones compartidas se identifican por relaciones, no por geometria.
    """
    from django.contrib.gis.db.models.aggregates import Union

    nivel = request.GET.get("nivel", "").strip().lower()
    if nivel not in ("zore", "are"):
        raise Http404("Tipo de expediente invalido")
    try:
        pk = int(request.GET.get("pk", ""))
    except (ValueError, TypeError):
        raise Http404("Identificador invalido")
    if pk < 1:
        raise Http404("Identificador invalido")
    propias = _asignaciones(nivel, pk)
    ids = {r.seccion_id for r in propias}
    if not ids:
        return JsonResponse({"vecinas": [], "geojson": {"type": "FeatureCollection", "features": []},
                             "zores_colindantes": []})
    geom = Seccion.objects.filter(pk__in=ids, geom__isnull=False).aggregate(union=Union("geom"))["union"]
    if geom is None:
        return JsonResponse({"vecinas": [], "geojson": {"type": "FeatureCollection", "features": []},
                             "zores_colindantes": []})
    # La interseccion de fronteras debe tener longitud positiva; un contacto
    # puntual carece de colindancia lineal para este informe.
    candidatas = list(Seccion.objects.filter(activa=True, geom__intersects=geom)
                      .exclude(pk__in=ids).select_related("municipio", "distrito_l", "distrito"))
    vecinas = []
    frontera = geom.boundary
    for seccion in candidatas:
        if seccion.geom is None:
            continue
        try:
            trazo = seccion.geom.boundary.intersection(frontera)
            metros = trazo.length
        except Exception:
            # Geometria irregular: se omite de este indicador informativo.
            continue
        if metros <= 0.001:
            continue
        # Ambas vistas (ARE y ZORE) usan este mismo JSON.
        # Claves de demarcacion tomadas directamente de Seccion.
        vecinas.append({
            "id": seccion.pk,
            "numero": seccion.seccion,
            "distrito": seccion.distrito.distrito,
            "distrito_url": reverse("pusinex:distrito", args=[seccion.distrito_id]),
            "distrito_local": seccion.distrito_l.distrito_local,
            "distrito_local_url": reverse("pusinex:distrito_local", args=[seccion.distrito_l_id]),
            "municipio_numero": seccion.municipio.municipio,
            "municipio": seccion.municipio.nombre,
            "municipio_url": reverse("pusinex:municipio", args=[seccion.municipio_id]),
            "url": reverse("pusinex:seccion", args=[seccion.pk]),
            "ares": [], "zores": [],
        })
    vecinas.sort(key=lambda x: x["numero"])
    by_id = {v["id"]: v for v in vecinas}
    zores = {}
    if by_id:
        asignaciones = (SeccionAre.objects.filter(seccion_id__in=by_id)
                        .select_related("are", "are__zore").order_by("are__numero"))
        for rel in asignaciones:
            v = by_id[rel.seccion_id]
            v["ares"].append({"numero": rel.are.numero,
                              "url": reverse("pusinex:are", args=[rel.are_id])})
            z = rel.are.zore
            if z.pk not in {item["id"] for item in v["zores"]}:
                v["zores"].append({"id": z.pk, "numero": z.numero,
                                    "distrito": z.distrito_id,
                                    "url": reverse("pusinex:zore", args=[z.pk])})
            if nivel == "zore" and z.pk == pk:
                continue
            zores[z.pk] = {"id": z.pk, "numero": z.numero, "distrito": z.distrito_id,
                           "url": reverse("pusinex:zore", args=[z.pk])}
    features = json.loads(serialize("geojson", Seccion.objects.filter(pk__in=by_id),
                                    geometry_field="geom", fields=("seccion",)))
    for feature in features["features"]:
        feature["properties"] = by_id[int(feature["id"])]
    return JsonResponse({"vecinas": vecinas, "geojson": features,
                         "zores_colindantes": sorted(zores.values(), key=lambda z: (z["distrito"], z["numero"]))},
                        json_dumps_params={"ensure_ascii": False})
