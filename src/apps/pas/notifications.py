"""Resumen diario y avisos por vencimiento, agrupados por destinatario."""
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from .agenda_service import construir_agenda
from .models import Accion, Ejecucion, Plan, PERIODICIDAD_UNICA, PERIODICIDAD_CONTINUA, PERIODICIDAD_MANUAL
from .notification_permissions import recibe_agenda
from .models import CalendarioNotificaciones
from django.contrib.auth import get_user_model
from apps.profiles.models import UnidadOrganizacional
from core.notification_schedule import CLAVES_AGENDA
from apps.pmml.delivery import correo_valido


def preparar_recurrencias():
    for actividad in Accion.objects.filter(
        plan__eliminacion=False,
        fecha_fin__isnull=True,
    ).exclude(periodicidad__in=[PERIODICIDAD_UNICA, PERIODICIDAD_CONTINUA, PERIODICIDAD_MANUAL]):
        actividad.generar_ejecuciones()


def fila(ejecucion):
    actividad = ejecucion.accion
    return {
        "actividad": strip_tags(actividad.accion), "plan": actividad.plan.nombre,
        "ejecucion": str(ejecucion), "fecha": ejecucion.fecha_fin,
        "responsable": ejecucion.responsable_display or "Sin responsable asignado",
        "prioridad": actividad.get_prioridad_display(),
        "evidencia": actividad.evidencia or "Evidencia de las actividades realizadas y los resultados obtenidos.",
        "url": settings.SITE_URL.rstrip("/") + reverse("pas:execution-evidence", args=[ejecucion.pk]),
    }


def crear_resumen(user, hoy):
    if hoy.weekday() not in CalendarioNotificaciones.dias_envio():
        return None
    agenda = recibe_agenda(user)
    secciones = []
    if agenda:
        context = construir_agenda(user, hoy)
        for key, title in (("urgentes", "Alarma"), ("requieren_atencion", "Faro"), ("vigilar", "Radar")):
            grupos = []
            for e in context[key]:
                item = fila(e)
                item.update({
                    "vencidas": [fila(v) for v in e.radar_vencidas],
                    "vencen_hoy": [fila(v) for v in e.radar_vencen_hoy],
                    "activas": [fila(v) for v in e.radar_activas],
                    "proxima": fila(e.radar_proxima_accion) if e.radar_proxima_accion else None,
                    "total": e.radar_total_pendientes,
                    "responsables": e.radar_responsables_operativos_display,
                })
                grupos.append(item)
            secciones.append({"nombre": title, "grupos": grupos})

    avisos = []
    replies = set()
    autoridades = {}
    for e in Ejecucion.objects.filter(
        responsable=user, completada=False, ciclo__fecha_fin__lte=hoy,
        ciclo__accion__plan__in=Plan.objects.visible_to(user),
        ciclo__accion__plan__eliminacion=False,
    ).select_related(
        "ciclo__accion__plan", "responsable__profile__unidad_organizacional",
    ).order_by("ciclo__fecha_fin", "pk"):
        perfil = getattr(user, "profile", None)
        unidad = perfil.unidad_organizacional if perfil else None
        clave = e.accion.puesto_responsable or (unidad.clave if unidad else "")
        cabecera = clave[0] + "0" if clave else ""
        if cabecera not in autoridades:
            candidatos = list(get_user_model().objects.filter(
                is_active=True, profile__unidad_organizacional__clave=cabecera,
                profile__unidad_organizacional__activa=True,
            ).select_related("profile__unidad_organizacional")) if cabecera in CLAVES_AGENDA else []
            autoridades[cabecera] = candidatos[0] if len(candidatos) == 1 else None
        titular = autoridades[cabecera]
        item = fila(e)
        item.update({
            "vencida": e.fecha_fin < hoy,
            "normativo": (titular.get_full_name().strip() or titular.username) if titular else "Responsable normativo",
            "cargo": titular.profile.unidad_organizacional.nombre if titular else "",
            "correo_normativo": titular.email if titular and correo_valido(titular.email) else "",
        })
        avisos.append(item)
        if item["correo_normativo"]:
            replies.add(item["correo_normativo"])

    if not any(section["grupos"] for section in secciones) and not avisos:
        return None
    context = {"nombre": user.get_full_name().strip() or user.username,
               "fecha": hoy, "secciones": secciones, "avisos": avisos,
               "site_url": settings.SITE_URL.rstrip("/")}
    return {
        "asunto": f"[PM]² {'Agenda' if agenda else 'Avisos de tareas'} — {hoy:%d/%m/%Y}",
        "texto": render_to_string("pas/correo_agenda.txt", context),
        "html": render_to_string("pas/correo_agenda.html", context),
        # Con varias autoridades, cada tarea indica su correo; evita respuestas masivas.
        "responder_a": sorted(replies) if len(replies) == 1 else [],
    }
