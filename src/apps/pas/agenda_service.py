"""Clasificación compartida por la agenda web y su resumen por correo."""
import datetime
from django.db.models import Q
from django.utils import timezone
from apps.profiles.models import UnidadOrganizacional
from .models import (Plan, Accion, Ejecucion, PERIODICIDAD_UNICA,
                     PERIODICIDAD_CONTINUA, PERIODICIDAD_MANUAL,
                     PRIORIDAD_CRITICA, PRIORIDAD_URGENTE)
from .permissions import usuarios_supervisados, obtener_claves_normativas_agenda


def construir_agenda(user, hoy=None):
    context = {}
    hoy = hoy or timezone.localdate()
    limite_atencion = hoy + datetime.timedelta(days=7)
    limite_vigilar = hoy + datetime.timedelta(days=14)
    inicio_semana = hoy - datetime.timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + datetime.timedelta(days=6)

    visible_plans = Plan.objects.visible_to(user)

    # Materializar la siguiente ocurrencia de recurrencias abiertas.
    actividades_recurrentes_abiertas = (
        Accion.objects.filter(
            plan__in=visible_plans,
            fecha_fin__isnull=True,
        )
        .exclude(
            periodicidad__in=[
                PERIODICIDAD_UNICA,
                PERIODICIDAD_CONTINUA,
                PERIODICIDAD_MANUAL,
            ]
        )
        .select_related(
            "plan",
            "responsable",
        )
    )

    for actividad in actividades_recurrentes_abiertas:
        actividad.generar_ejecuciones()

    # Alcance operativo.
    perfil = getattr(
        user,
        "profile",
        None,
    )

    if perfil:
        usuarios_agenda = list(usuarios_supervisados(user))
    else:
        usuarios_agenda = [user]

    usuarios_agenda_ids = {
        usuario.pk for usuario in usuarios_agenda
    }

    es_supervisor_agenda = (
        perfil.es_supervisor_agenda if perfil else False
    )

    # Alcance normativo.
    claves_normativas = (
        obtener_claves_normativas_agenda(perfil)
        if perfil
        else set()
    )

    claves_unidades = set(claves_normativas)

    claves_unidades.update(
        Accion.objects.filter(
            plan__in=visible_plans,
            puesto_responsable__isnull=False,
        )
        .exclude(puesto_responsable="")
        .values_list(
            "puesto_responsable",
            flat=True,
        )
    )

    unidades_normativas = {
        unidad.clave: unidad
        for unidad in UnidadOrganizacional.objects.filter(
            clave__in=claves_unidades
        )
    }

    # Universo visible de ejecuciones.
    ejecuciones = list(
        Ejecucion.objects.filter(
            (
                Q(responsable__in=usuarios_agenda)
                | Q(
                    ciclo__accion__puesto_responsable__in=(
                        claves_normativas
                    )
                )
            ),
            ciclo__accion__plan__in=visible_plans,
        )
        .select_related(
            "ciclo",
            "ciclo__accion",
            "ciclo__accion__plan",
            "ciclo__accion__responsable",
            "ciclo__accion__responsable__profile",
            "responsable",
            "responsable__profile",
            "responsable__profile__unidad_organizacional",
        )
        .prefetch_related(
            "evidencias",
        )
        .distinct()
        .order_by(
            "ciclo__accion_id",
            "ciclo__fecha_fin",
            "ciclo__fecha_inicio",
            "ambito",
            "pk",
        )
    )

    def nombre_operativo(usuario):
        if not usuario:
            return "—"

        perfil_usuario = getattr(
            usuario,
            "profile",
            None,
        )

        if perfil_usuario:
            return perfil_usuario.nombre_calendario

        return (
            usuario.get_full_name() or usuario.username
        )[:10]

    def nombre_normativo(actividad):
        if not actividad.puesto_responsable:
            return "—"

        unidad = unidades_normativas.get(
            actividad.puesto_responsable
        )

        if unidad:
            return unidad.etiqueta_funcional

        return actividad.puesto_responsable

    # Enriquecimiento básico.
    for ejecucion in ejecuciones:
        actividad = ejecucion.accion

        ejecucion.es_mia = (
            ejecucion.responsable_id == user.id
        )

        ejecucion.visible_por_operacion = (
            ejecucion.responsable_id in usuarios_agenda_ids
        )

        ejecucion.visible_por_normativa = (
            bool(actividad.puesto_responsable)
            and actividad.puesto_responsable in claves_normativas
        )

        ejecucion.responsable_operativo_display = (
            nombre_operativo(ejecucion.responsable)
        )

        ejecucion.responsable_normativo_display = (
            nombre_normativo(actividad)
        )

    # Agrupar pendientes por actividad.
    grupos = {}
    terminadas = []

    for ejecucion in ejecuciones:
        if ejecucion.completada:
            terminadas.append(ejecucion)
            continue

        actividad_id = ejecucion.accion.pk
        grupos.setdefault(actividad_id, [])
        grupos[actividad_id].append(ejecucion)

    urgente = []
    atencion = []
    vigilar = []

    total_ejecuciones_vencidas = 0
    total_vencen_hoy = 0

    for ejecuciones_actividad in grupos.values():
        ejecuciones_actividad.sort(
            key=lambda ejecucion: (
                ejecucion.fecha_fin,
                ejecucion.fecha_inicio,
                ejecucion.pk,
            )
        )

        actividad = ejecuciones_actividad[0].accion
        es_continua = (
            actividad.periodicidad == PERIODICIDAD_CONTINUA
        )

        vencidas_actividad = [
            ejecucion
            for ejecucion in ejecuciones_actividad
            if ejecucion.fecha_fin < hoy
        ]

        vencen_hoy_actividad = [
            ejecucion
            for ejecucion in ejecuciones_actividad
            if ejecucion.fecha_fin == hoy
        ]

        activas_actividad = [
            ejecucion
            for ejecucion in ejecuciones_actividad
            if ejecucion.fecha_inicio <= hoy < ejecucion.fecha_fin
        ]

        futuras_actividad = [
            ejecucion
            for ejecucion in ejecuciones_actividad
            if ejecucion.fecha_inicio > hoy
        ]

        proxima_accion = (
            futuras_actividad[0] if futuras_actividad else None
        )

        nombres_operativos = []

        for ejecucion in ejecuciones_actividad:
            nombre = ejecucion.responsable_operativo_display

            if (
                nombre
                and nombre != "—"
                and nombre not in nombres_operativos
            ):
                nombres_operativos.append(nombre)

        responsables_operativos_display = (
            ", ".join(nombres_operativos)
            if nombres_operativos
            else "—"
        )

        ambitos = []

        for ejecucion in ejecuciones_actividad:
            ambito = ejecucion.get_ambito_display()

            if ambito not in ambitos:
                ambitos.append(ambito)

        ambitos_display = ", ".join(ambitos)

        # Seleccionar la ejecución representativa.
        if vencidas_actividad:
            representativa = vencidas_actividad[0]
        elif vencen_hoy_actividad:
            representativa = vencen_hoy_actividad[0]
        elif activas_actividad:
            representativa = activas_actividad[0]
        elif proxima_accion:
            representativa = proxima_accion
        else:
            representativa = ejecuciones_actividad[0]

        representativa.radar_vencidas = vencidas_actividad
        representativa.radar_vencidas_count = len(
            vencidas_actividad
        )
        representativa.radar_vencen_hoy = vencen_hoy_actividad
        representativa.radar_vencen_hoy_count = len(
            vencen_hoy_actividad
        )
        representativa.radar_proxima_accion = proxima_accion
        representativa.radar_activas = activas_actividad
        representativa.radar_responsables_operativos_display = (
            responsables_operativos_display
        )
        representativa.radar_ambitos_display = ambitos_display
        representativa.radar_total_pendientes = len(
            ejecuciones_actividad
        )

        representativa.es_mia = any(
            ejecucion.responsable_id == user.id
            for ejecucion in ejecuciones_actividad
        )

        representativa.responsable_operativo_display = (
            responsables_operativos_display
        )
        representativa.responsable_normativo_display = (
            nombre_normativo(actividad)
        )

        total_ejecuciones_vencidas += len(vencidas_actividad)
        total_vencen_hoy += len(vencen_hoy_actividad)

        # Atención inmediata.
        if vencidas_actividad:
            representativa.radar_motivo = "vencida"
            urgente.append(representativa)
            continue

        if vencen_hoy_actividad:
            representativa.radar_motivo = "vence_hoy"
            urgente.append(representativa)
            continue

        if es_continua and activas_actividad:
            dias_restantes = (
                representativa.fecha_fin - hoy
            ).days

            if dias_restantes == 1:
                representativa.radar_motivo = "continua_inmediata"
                urgente.append(representativa)
                continue

        if (
            activas_actividad
            and actividad.prioridad == PRIORIDAD_CRITICA
        ):
            representativa.radar_motivo = "critica_activa"
            urgente.append(representativa)
            continue

        # Atención próxima.
        if es_continua and activas_actividad:
            dias_restantes = (
                representativa.fecha_fin - hoy
            ).days

            if 2 <= dias_restantes <= 5:
                representativa.radar_motivo = "continua_proxima"
                atencion.append(representativa)
                continue

        if proxima_accion:
            if proxima_accion.fecha_inicio <= limite_atencion:
                representativa.radar_motivo = "proxima_7_dias"
                atencion.append(representativa)
                continue

        if (
            activas_actividad
            and actividad.prioridad == PRIORIDAD_URGENTE
        ):
            representativa.radar_motivo = "urgente_activa"
            atencion.append(representativa)
            continue

        # Vigilancia.
        if activas_actividad:
            representativa.radar_motivo = "activa"
            vigilar.append(representativa)
            continue

        if proxima_accion:
            if proxima_accion.fecha_inicio <= limite_vigilar:
                representativa.radar_motivo = "proxima_14_dias"
                vigilar.append(representativa)
                continue

    urgente.sort(
        key=lambda ejecucion: (
            ejecucion.fecha_fin,
            ejecucion.accion.pk,
        )
    )

    atencion.sort(
        key=lambda ejecucion: (
            (
                ejecucion.radar_proxima_accion.fecha_inicio
                if ejecucion.radar_proxima_accion
                else ejecucion.fecha_fin
            ),
            ejecucion.accion.pk,
        )
    )

    vigilar.sort(
        key=lambda ejecucion: (
            (
                ejecucion.radar_proxima_accion.fecha_inicio
                if ejecucion.radar_proxima_accion
                else ejecucion.fecha_fin
            ),
            ejecucion.accion.pk,
        )
    )

    context.update(
        {
            "hoy": hoy,
            "inicio_semana": inicio_semana,
            "fin_semana": fin_semana,
            "limite_atencion": limite_atencion,
            "limite_vigilar": limite_vigilar,
            "usuarios_agenda": usuarios_agenda,
            "usuarios_agenda_ids": usuarios_agenda_ids,
            "es_supervisor_agenda": es_supervisor_agenda,
            "total_usuarios_agenda": len(usuarios_agenda),
            "claves_normativas": claves_normativas,
            "urgentes": urgente,
            "requieren_atencion": atencion,
            "vigilar": vigilar,
            "terminadas": terminadas,
            "total_urgentes": len(urgente),
            "total_requieren_atencion": len(atencion),
            "total_vigilar": len(vigilar),
            "total_vencidas": total_ejecuciones_vencidas,
            "total_vencen_hoy": total_vencen_hoy,
            "total_terminadas": len(terminadas),
            # Compatibilidad temporal.
            "vencidas": [],
            "vencen_hoy": [],
            "vencen_semana": [],
            "prioridad_alta": [],
            "inician_hoy": [],
            "inician_semana": [],
            "total_vencen_semana": len(atencion),
            "total_prioridad_alta": 0,
            "total_inician_hoy": 0,
            "total_inician_semana": len(vigilar),
        }
    )

    return context
