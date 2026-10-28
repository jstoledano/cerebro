import json

import datetime
from datetime import date

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Prefetch, Q
from django.http import (
    HttpResponse,
    FileResponse,
    Http404,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    DeleteView,
    TemplateView,
    View,
)
from .forms import (
    PlanForm,
    AccionForm,
    PlanClosureForm,
    EvidenciaForm,
)
from .models import (
    Plan,
    Accion,
    Evidencia,
    CicloActividad,
    Ejecucion,
    AMBITO,
    PERIODICIDAD_UNICA,
    PERIODICIDAD_MANUAL,
    FORMATO_SIN_EVIDENCIA,
    PERIODICIDAD_SEMANAL,
    PERIODICIDAD_QUINCENAL,
    PERIODICIDAD_MENSUAL,
    PERIODICIDAD_BIMESTRAL,
    PERIODICIDAD_TRIMESTRAL,
    PERIODICIDAD_ANUAL,
    PRIORIDAD_URGENTE,
    PRIORIDAD_CRITICA,
    PERIODICIDAD_CONTINUA,
)
from apps.profiles.models import (
    UnidadOrganizacional,
)


def hx_trigger_header(*events):
    if not events:
        return ""
    payload = {event: "" for event in events}
    return json.dumps(payload)


def obtener_claves_normativas_agenda(
    perfil,
):
    """
    Devuelve las claves organizacionales cuya
    responsabilidad normativa debe ser visible
    en la agenda del perfil.

    Regla:

    - Un usuario ve su propia unidad y sus
      descendientes.
    - Si pertenece a una unidad cabecera de Junta
      Local de dos dígitos terminada en 0, también
      supervisa funcionalmente los capítulos
      equivalentes de las juntas distritales.

    Ejemplo para la unidad 50:

        50
        5010
        5020
        5030
        5040
        5050
        5099

        51
        5110
        5199

        52
        5210
        5299

        53
        5310
        5399
    """

    if (
        not perfil
        or not perfil.unidad_organizacional_id
    ):
        return set()

    unidad = (
        perfil.unidad_organizacional
    )

    unidades = {
        item.clave
        for item
        in unidad.obtener_descendientes(
            incluir_self=True
        )
    }

    clave = unidad.clave

    # ------------------------------------------------------
    # Cabecera funcional de Junta Local.
    #
    # Ejemplo:
    #
    # 50 -> 50, 51, 52, 53 y sus descendientes.
    # 20 -> 20, 21, 22, 23 y sus descendientes.
    # ------------------------------------------------------

    if (
        unidad.site == 0
        and len(clave) == 2
        and clave.endswith("0")
    ):
        prefijo_funcional = (
            clave[0]
        )

        unidades_equivalentes = (
            UnidadOrganizacional.objects
            .filter(
                activa=True,
                clave__in=[
                    f"{prefijo_funcional}0",
                    f"{prefijo_funcional}1",
                    f"{prefijo_funcional}2",
                    f"{prefijo_funcional}3",
                ],
            )
            .order_by(
                "clave"
            )
        )

        for unidad_equivalente in (
            unidades_equivalentes
        ):
            for item in (
                unidad_equivalente
                .obtener_descendientes(
                    incluir_self=True
                )
            ):
                unidades.add(
                    item.clave
                )

    return unidades


def usuario_puede_gestionar_ejecucion(
    user,
    execution,
):
    """
    Determina si un usuario puede cerrar o reabrir
    una ejecución concreta.

    Pueden hacerlo:

    - el creador del plan;
    - el responsable operativo de la ejecución;
    - quien tenga responsabilidad normativa sobre
      la actividad;
    - un supervisor funcional de esa responsabilidad;
    - quien tenga permiso change_ejecucion;
    - un superusuario.
    """

    if (
        not user
        or not user.is_authenticated
    ):
        return False

    if user.is_superuser:
        return True

    if user.has_perm(
        "pas.change_ejecucion"
    ):
        return True

    # ------------------------------------------------------
    # Responsable operativo
    # ------------------------------------------------------

    if (
        execution.responsable_id
        == user.id
    ):
        return True

    plan = execution.plan

    # ------------------------------------------------------
    # Creador del plan
    # ------------------------------------------------------

    if (
        plan.user_id
        and plan.user_id == user.id
    ):
        return True

    # ------------------------------------------------------
    # Responsabilidad normativa
    # ------------------------------------------------------

    actividad = execution.accion

    if not actividad.puesto_responsable:
        return False

    perfil = getattr(
        user,
        "profile",
        None,
    )

    if not perfil:
        return False

    claves_normativas = (
        obtener_claves_normativas_agenda(
            perfil
        )
    )

    return (
        actividad.puesto_responsable
        in claves_normativas
    )


@method_decorator(
    login_required,
    name="dispatch",
)
class PASIndex(ListView):
    model = Plan
    template_name = "pas/index.html"

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        plan_actions_prefetch = Prefetch(
            "accion_set",
            queryset=(
                Accion.objects.select_related(
                    "responsable",
                    "responsable__profile",
                ).prefetch_related(
                    "ciclos__ejecuciones",
                )
            ),
            to_attr="pas_actions",
        )

        plan_list = (
            Plan.objects.visible_to(self.request.user)
            .prefetch_related(plan_actions_prefetch)
            .order_by("-fecha_llenado")
        )

        def state_priority(
            estado,
        ):
            if estado == "Abierta Fuera de Tiempo":
                return 0

            if estado == "Cerrada":
                return 3

            if estado == "Abierta en Tiempo":
                return 2

            return 1

        action_items = []

        action_qs = (
            Accion.objects.filter(plan__in=plan_list)
            .select_related(
                "plan",
                "responsable",
                "responsable__profile",
            )
            .prefetch_related(
                "ciclos__ejecuciones",
            )
        )

        for action in action_qs:
            estado = action.get_estado

            if estado == "Cerrada":
                continue

            priority = state_priority(estado)

            action_items.append(
                (
                    priority,
                    action.fecha_fin or date.max,
                    action.pk,
                    action,
                )
            )

        action_items.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
            )
        )

        action_list = [item[3] for item in action_items]

        for plan in plan_list:
            cerradas = 0
            abiertas_en_tiempo = 0
            abiertas_fuera_de_tiempo = 0

            for accion in plan.pas_actions:
                estado = accion.get_estado

                if estado == "Cerrada":
                    cerradas += 1

                elif estado == "Abierta en Tiempo":
                    abiertas_en_tiempo += 1

                elif estado == "Abierta Fuera de Tiempo":
                    abiertas_fuera_de_tiempo += 1

            plan.cerradas = cerradas

            plan.abiertas_en_tiempo = abiertas_en_tiempo

            plan.abiertas_fuera_de_tiempo = abiertas_fuera_de_tiempo

            plan.total_actividades = (
                cerradas + abiertas_en_tiempo + abiertas_fuera_de_tiempo
            )

        context["plan_list"] = plan_list

        context["action_list"] = action_list

        return context


@method_decorator(
    login_required,
    name="dispatch",
)
class AgendaView(TemplateView):
    template_name = "pas/agenda.html"

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        hoy = timezone.localdate()

        limite_atencion = hoy + datetime.timedelta(days=7)

        limite_vigilar = hoy + datetime.timedelta(days=14)

        inicio_semana = hoy - datetime.timedelta(days=hoy.weekday())

        fin_semana = inicio_semana + datetime.timedelta(days=6)

        visible_plans = Plan.objects.visible_to(self.request.user)

        # ======================================================
        # Mantener materializada la siguiente ocurrencia
        # de las recurrencias abiertas.
        #
        # Continua no entra aquí: es un único intervalo
        # y exige fecha de término.
        # ======================================================

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

        # ======================================================
        # Alcance operativo
        # ======================================================

        perfil = getattr(
            self.request.user,
            "profile",
            None,
        )

        if perfil:
            usuarios_agenda = list(perfil.obtener_usuarios_agenda())
        else:
            usuarios_agenda = [self.request.user]

        usuarios_agenda_ids = {usuario.pk for usuario in usuarios_agenda}

        es_supervisor_agenda = perfil.es_supervisor_agenda if perfil else False

        # ======================================================
        # Alcance normativo
        # ======================================================

        claves_normativas = (
            obtener_claves_normativas_agenda(perfil) if perfil else set()
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
            for unidad in (
                UnidadOrganizacional.objects.filter(clave__in=claves_unidades)
            )
        }

        # ======================================================
        # Universo visible de ejecuciones
        # ======================================================

        ejecuciones = list(
            Ejecucion.objects.filter(
                (
                    Q(responsable__in=(usuarios_agenda))
                    | Q(ciclo__accion__puesto_responsable__in=(claves_normativas))
                ),
                ciclo__accion__plan__in=(visible_plans),
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
                "evidencia_registrada",
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

        # ======================================================
        # Helpers de presentación
        # ======================================================

        def nombre_operativo(
            usuario,
        ):
            if not usuario:
                return "—"

            perfil_usuario = getattr(
                usuario,
                "profile",
                None,
            )

            if perfil_usuario:
                return perfil_usuario.nombre_calendario

            return (usuario.get_full_name() or usuario.username)[:10]

        def nombre_normativo(
            actividad,
        ):
            if not (actividad.puesto_responsable):
                return "—"

            unidad = unidades_normativas.get(actividad.puesto_responsable)

            if unidad:
                return unidad.etiqueta_funcional

            return actividad.puesto_responsable

        # ======================================================
        # Enriquecimiento básico
        # ======================================================

        for ejecucion in ejecuciones:
            actividad = ejecucion.accion

            ejecucion.es_mia = ejecucion.responsable_id == self.request.user.id

            ejecucion.visible_por_operacion = (
                ejecucion.responsable_id in usuarios_agenda_ids
            )

            ejecucion.visible_por_normativa = bool(actividad.puesto_responsable) and (
                actividad.puesto_responsable in claves_normativas
            )

            ejecucion.responsable_operativo_display = nombre_operativo(
                ejecucion.responsable
            )

            ejecucion.responsable_normativo_display = nombre_normativo(actividad)

        # ======================================================
        # Agrupar por actividad
        # ======================================================

        grupos = {}

        terminadas = []

        for ejecucion in ejecuciones:
            if ejecucion.completada:
                terminadas.append(ejecucion)
                continue

            actividad_id = ejecucion.accion.pk

            grupos.setdefault(
                actividad_id,
                [],
            )

            grupos[actividad_id].append(ejecucion)

        # ======================================================
        # Resultado del radar
        # ======================================================

        urgente = []
        atencion = []
        vigilar = []

        total_ejecuciones_vencidas = 0
        total_vencen_hoy = 0

        # ======================================================
        # Analizar una actividad completa
        # ======================================================

        for ejecuciones_actividad in grupos.values():
            ejecuciones_actividad.sort(
                key=lambda ejecucion: (
                    ejecucion.fecha_fin,
                    ejecucion.fecha_inicio,
                    ejecucion.pk,
                )
            )

            actividad = ejecuciones_actividad[0].accion

            es_continua = actividad.periodicidad == PERIODICIDAD_CONTINUA

            # --------------------------------------------------
            # Situación histórica / actual
            # --------------------------------------------------

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
                if (ejecucion.fecha_inicio <= hoy < ejecucion.fecha_fin)
            ]

            futuras_actividad = [
                ejecucion
                for ejecucion in ejecuciones_actividad
                if ejecucion.fecha_inicio > hoy
            ]

            # --------------------------------------------------
            # Próxima acción
            # --------------------------------------------------

            proxima_accion = futuras_actividad[0] if futuras_actividad else None

            # --------------------------------------------------
            # Responsables operativos
            # --------------------------------------------------

            nombres_operativos = []

            for ejecucion in ejecuciones_actividad:
                nombre = ejecucion.responsable_operativo_display

                if nombre and nombre != "—" and nombre not in nombres_operativos:
                    nombres_operativos.append(nombre)

            responsables_operativos_display = (
                ", ".join(nombres_operativos) if nombres_operativos else "—"
            )

            # --------------------------------------------------
            # Ámbitos
            # --------------------------------------------------

            ambitos = []

            for ejecucion in ejecuciones_actividad:
                ambito = ejecucion.get_ambito_display()

                if ambito not in ambitos:
                    ambitos.append(ambito)

            ambitos_display = ", ".join(ambitos)

            # --------------------------------------------------
            # Ejecución representativa
            # --------------------------------------------------

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

            # ==================================================
            # Datos agregados
            # ==================================================

            representativa.radar_vencidas = vencidas_actividad

            representativa.radar_vencidas_count = len(vencidas_actividad)

            representativa.radar_vencen_hoy = vencen_hoy_actividad

            representativa.radar_vencen_hoy_count = len(vencen_hoy_actividad)

            representativa.radar_proxima_accion = proxima_accion

            representativa.radar_activas = activas_actividad

            representativa.radar_responsables_operativos_display = (
                responsables_operativos_display
            )

            representativa.radar_ambitos_display = ambitos_display

            representativa.radar_total_pendientes = len(ejecuciones_actividad)

            representativa.es_mia = any(
                ejecucion.responsable_id == self.request.user.id
                for ejecucion in ejecuciones_actividad
            )

            representativa.responsable_operativo_display = (
                responsables_operativos_display
            )

            representativa.responsable_normativo_display = nombre_normativo(actividad)

            # --------------------------------------------------
            # Contadores globales
            # --------------------------------------------------

            total_ejecuciones_vencidas += len(vencidas_actividad)

            total_vencen_hoy += len(vencen_hoy_actividad)

            # ==================================================
            # CLASIFICACIÓN
            #
            # Una actividad entra en una sola categoría.
            # ==================================================

            # --------------------------------------------------
            # 1. REQUIERE ATENCIÓN INMEDIATA
            # --------------------------------------------------

            if vencidas_actividad:
                representativa.radar_motivo = "vencida"

                urgente.append(representativa)

                continue

            if vencen_hoy_actividad:
                representativa.radar_motivo = "vence_hoy"

                urgente.append(representativa)

                continue

            # --------------------------------------------------
            # Continua activa: D-1
            # --------------------------------------------------

            if es_continua and activas_actividad:
                dias_restantes = (representativa.fecha_fin - hoy).days

                if dias_restantes == 1:
                    representativa.radar_motivo = "continua_inmediata"

                    urgente.append(representativa)

                    continue

            if activas_actividad and actividad.prioridad == PRIORIDAD_CRITICA:
                representativa.radar_motivo = "critica_activa"

                urgente.append(representativa)

                continue

            # --------------------------------------------------
            # 2. REQUIERE ATENCIÓN
            # --------------------------------------------------

            # --------------------------------------------------
            # Continua activa: D-5 a D-2
            # --------------------------------------------------

            if es_continua and activas_actividad:
                dias_restantes = (representativa.fecha_fin - hoy).days

                if 2 <= dias_restantes <= 5:
                    representativa.radar_motivo = "continua_proxima"

                    atencion.append(representativa)

                    continue

            # --------------------------------------------------
            # Próxima ejecución dentro de 7 días
            # --------------------------------------------------

            if proxima_accion:
                if proxima_accion.fecha_inicio <= limite_atencion:
                    representativa.radar_motivo = "proxima_7_dias"

                    atencion.append(representativa)

                    continue

            if activas_actividad and actividad.prioridad == PRIORIDAD_URGENTE:
                representativa.radar_motivo = "urgente_activa"

                atencion.append(representativa)

                continue

            # --------------------------------------------------
            # 3. VIGILAR
            # --------------------------------------------------

            if activas_actividad:
                representativa.radar_motivo = "activa"

                vigilar.append(representativa)

                continue

            if proxima_accion:
                if proxima_accion.fecha_inicio <= limite_vigilar:
                    representativa.radar_motivo = "proxima_14_dias"

                    vigilar.append(representativa)

                    continue

        # ======================================================
        # Orden
        # ======================================================

        urgente.sort(
            key=lambda ejecucion: (
                ejecucion.fecha_fin,
                ejecucion.accion.pk,
            )
        )

        atencion.sort(
            key=lambda ejecucion: (
                (ejecucion.radar_proxima_accion.fecha_inicio)
                if (ejecucion.radar_proxima_accion)
                else ejecucion.fecha_fin,
                ejecucion.accion.pk,
            )
        )

        vigilar.sort(
            key=lambda ejecucion: (
                (ejecucion.radar_proxima_accion.fecha_inicio)
                if (ejecucion.radar_proxima_accion)
                else ejecucion.fecha_fin,
                ejecucion.accion.pk,
            )
        )

        # ======================================================
        # Contexto
        # ======================================================

        context.update(
            {
                "hoy": hoy,
                "inicio_semana": (inicio_semana),
                "fin_semana": (fin_semana),
                "limite_atencion": (limite_atencion),
                "limite_vigilar": (limite_vigilar),
                "usuarios_agenda": (usuarios_agenda),
                "usuarios_agenda_ids": (usuarios_agenda_ids),
                "es_supervisor_agenda": (es_supervisor_agenda),
                "total_usuarios_agenda": (len(usuarios_agenda)),
                "claves_normativas": (claves_normativas),
                "urgentes": (urgente),
                "requieren_atencion": (atencion),
                "vigilar": (vigilar),
                "terminadas": (terminadas),
                "total_urgentes": (len(urgente)),
                "total_requieren_atencion": (len(atencion)),
                "total_vigilar": (len(vigilar)),
                "total_vencidas": (total_ejecuciones_vencidas),
                "total_vencen_hoy": (total_vencen_hoy),
                "total_terminadas": (len(terminadas)),
                # Compatibilidad temporal
                "vencidas": [],
                "vencen_hoy": [],
                "vencen_semana": [],
                "prioridad_alta": [],
                "inician_hoy": [],
                "inician_semana": [],
                "total_vencen_semana": (len(atencion)),
                "total_prioridad_alta": 0,
                "total_inician_hoy": 0,
                "total_inician_semana": (len(vigilar)),
            }
        )

        return context


class CalendarEventsView(View):
    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        start_value = request.GET.get(
            "start"
        )

        end_value = request.GET.get(
            "end"
        )

        try:
            fecha_inicio = (
                date.fromisoformat(
                    start_value[:10]
                )
                if start_value
                else None
            )

            fecha_fin = (
                date.fromisoformat(
                    end_value[:10]
                )
                if end_value
                else None
            )

        except ValueError:
            return JsonResponse(
                {
                    "error": (
                        "El rango de fechas "
                        "no es válido."
                    )
                },
                status=400,
            )

        visible_plans = (
            Plan.objects.visible_to(
                request.user
            )
        )

        # ======================================================
        # Perfil y alcance de agenda
        # ======================================================

        perfil = getattr(
            request.user,
            "profile",
            None,
        )

        if perfil:
            responsables = list(
                perfil.obtener_usuarios_agenda()
            )

            es_supervisor_agenda = (
                perfil.es_supervisor_agenda
            )

            claves_normativas = (
                obtener_claves_normativas_agenda(
                    perfil
                )
            )

        else:
            responsables = [
                request.user
            ]

            es_supervisor_agenda = False

            claves_normativas = set()

        responsables_ids = {
            usuario.pk
            for usuario
            in responsables
        }

        # ======================================================
        # Catálogo organizacional
        # ======================================================

        unidades_organizacionales = {
            unidad.clave: unidad
            for unidad
            in (
                UnidadOrganizacional.objects
                .filter(
                    activa=True
                )
            )
        }

        def unidad_por_clave(
            clave,
        ):
            if not clave:
                return None

            return (
                unidades_organizacionales
                .get(
                    clave
                )
            )

        def responsable_normativo_display(
            actividad,
        ):
            if not (
                actividad
                .puesto_responsable
            ):
                return ""

            unidad = unidad_por_clave(
                actividad
                .puesto_responsable
            )

            if not unidad:
                return (
                    actividad
                    .puesto_responsable
                )

            return (
                unidad
                .etiqueta_funcional
            )

        def unidad_operativa_display(
            usuario,
        ):
            if not usuario:
                return ""

            perfil_usuario = getattr(
                usuario,
                "profile",
                None,
            )

            if (
                not perfil_usuario
                or not (
                    perfil_usuario
                    .unidad_organizacional
                )
            ):
                return ""

            unidad = (
                perfil_usuario
                .unidad_organizacional
            )

            return (
                unidad
                .nombre_funcional
            )

        def nombre_calendario(
            usuario,
        ):
            if not usuario:
                return ""

            perfil_usuario = getattr(
                usuario,
                "profile",
                None,
            )

            if perfil_usuario:
                return (
                    perfil_usuario
                    .nombre_calendario
                )

            return (
                usuario.get_full_name()
                or usuario.username
            )[:10]

        # ======================================================
        # Ejecuciones materializadas
        # ======================================================

        ejecuciones = (
            Ejecucion.objects
            .filter(
                (
                    Q(
                        responsable__in=(
                            responsables
                        )
                    )
                    |
                    Q(
                        ciclo__accion__puesto_responsable__in=(
                            claves_normativas
                        )
                    )
                ),
                ciclo__accion__plan__in=(
                    visible_plans
                ),
            )
            .select_related(
                "ciclo",
                "ciclo__accion",
                "ciclo__accion__plan",
                "ciclo__accion__responsable",
                "responsable",
                "responsable__profile",
                "responsable__profile__unidad_organizacional",
            )
            .prefetch_related(
                "evidencia_registrada",
            )
            .distinct()
            .order_by(
                "ciclo__fecha_inicio",
                "ciclo__fecha_fin",
                "responsable__first_name",
                "responsable__last_name",
                "pk",
            )
        )

        # ======================================================
        # Intersección con el rango visible
        #
        # Antes sólo se filtraba por fecha_fin. Eso excluía
        # actividades largas que empezaban antes del mes y
        # terminaban después.
        #
        # Una ejecución entra si:
        #
        # inicio < final del rango
        # y
        # fin >= inicio del rango
        # ======================================================

        if (
            fecha_inicio
            and fecha_fin
        ):
            ejecuciones = (
                ejecuciones.filter(
                    ciclo__fecha_inicio__lt=(
                        fecha_fin
                    ),
                    ciclo__fecha_fin__gte=(
                        fecha_inicio
                    ),
                )
            )

        elif fecha_inicio:
            ejecuciones = (
                ejecuciones.filter(
                    ciclo__fecha_fin__gte=(
                        fecha_inicio
                    )
                )
            )

        elif fecha_fin:
            ejecuciones = (
                ejecuciones.filter(
                    ciclo__fecha_inicio__lt=(
                        fecha_fin
                    )
                )
            )

        eventos = []

        eventos_existentes = set()

        hoy = timezone.localdate()

        for ejecucion in ejecuciones:
            accion = ejecucion.accion

            actividad = (
                strip_tags(
                    accion.accion
                    or ""
                )
                .strip()
            )

            if not actividad:
                actividad = (
                    f"Actividad {accion.pk}"
                )

            # --------------------------------------------------
            # Evidencia
            # --------------------------------------------------

            if (
                accion.formato_evidencia
                == FORMATO_SIN_EVIDENCIA
            ):
                evidencia_estado = (
                    "No requerida"
                )

            elif ejecucion.tiene_evidencia:
                evidencia_estado = (
                    "Registrada"
                )

            else:
                evidencia_estado = (
                    "Pendiente"
                )

            # --------------------------------------------------
            # Responsabilidades
            # --------------------------------------------------

            responsable_operativo = (
                nombre_calendario(
                    ejecucion.responsable
                )
            )

            responsable_normativo = (
                responsable_normativo_display(
                    accion
                )
            )

            unidad_operativa = (
                unidad_operativa_display(
                    ejecucion.responsable
                )
            )

            es_mia = (
                ejecucion.responsable_id
                == request.user.id
            )

            visible_por_operacion = (
                ejecucion.responsable_id
                in responsables_ids
            )

            visible_por_normativa = (
                bool(
                    accion
                    .puesto_responsable
                )
                and (
                    accion
                    .puesto_responsable
                    in claves_normativas
                )
            )

            # --------------------------------------------------
            # Título
            # --------------------------------------------------

            if es_supervisor_agenda:

                if es_mia:
                    titulo = (
                        f"YO — {actividad}"
                    )

                elif responsable_operativo:
                    titulo = (
                        f"{responsable_operativo} "
                        f"— {actividad}"
                    )

                elif responsable_normativo:
                    titulo = (
                        f"{responsable_normativo} "
                        f"— {actividad}"
                    )

                else:
                    titulo = actividad

            else:
                titulo = actividad

            # ==================================================
            # Representación temporal
            #
            # Continua:
            # fecha_inicio -> fecha_fin completa.
            #
            # FullCalendar interpreta "end" como exclusivo.
            #
            # Las demás periodicidades permanecen como eventos
            # puntuales sobre su fecha de término.
            # ==================================================

            es_continua = (
                accion.periodicidad
                == PERIODICIDAD_CONTINUA
            )

            if es_continua:
                event_start = (
                    ejecucion
                    .fecha_inicio
                    .isoformat()
                )

                event_end = (
                    ejecucion
                    .fecha_fin
                    + datetime.timedelta(
                        days=1
                    )
                ).isoformat()

            else:
                event_start = (
                    ejecucion
                    .fecha_fin
                    .isoformat()
                )

                event_end = None

            eventos_existentes.add(
                (
                    accion.pk,
                    ejecucion.ambito,
                    ejecucion.fecha_fin,
                )
            )

            evento = {
                "id": str(
                    ejecucion.pk
                ),
                "title": titulo,
                "start": event_start,
                "allDay": True,
                "extendedProps": {
                    "activityId": (
                        accion.pk
                    ),
                    "planId": (
                        ejecucion.plan.pk
                    ),
                    "plan": (
                        ejecucion.plan.nombre
                    ),
                    "planUrl": reverse(
                        "pas:detalle",
                        args=[
                            ejecucion.plan.pk
                        ],
                    ),
                    "activityDetailUrl": reverse(
                        "pas:activity-detail",
                        args=[
                            accion.pk
                        ],
                    ),
                    "folio": (
                        ejecucion.plan.folio
                        or ""
                    ),
                    "ciclo": (
                        ejecucion
                        .ciclo
                        .etiqueta
                    ),
                    "ambito": (
                        ejecucion
                        .get_ambito_display()
                    ),
                    "responsable": (
                        responsable_operativo
                    ),
                    "responsableOperativo": (
                        responsable_operativo
                    ),
                    "responsableNormativo": (
                        responsable_normativo
                    ),
                    "unidadOperativa": (
                        unidad_operativa
                    ),
                    "visiblePorOperacion": (
                        visible_por_operacion
                    ),
                    "visiblePorNormativa": (
                        visible_por_normativa
                    ),
                    "estado": (
                        ejecucion.estado_agenda
                    ),
                    "estadoDisplay": (
                        ejecucion
                        .estado_agenda_display
                    ),
                    "evidencia": (
                        evidencia_estado
                    ),
                    "completada": (
                        ejecucion.completada
                    ),
                    "esMia": es_mia,
                    "proyectada": False,
                    "continua": (
                        es_continua
                    ),
                },
            }

            if event_end:
                evento[
                    "end"
                ] = event_end

            eventos.append(
                evento
            )

        # ======================================================
        # Proyecciones de recurrencias
        #
        # Continua NO entra aquí porque ya cuenta con un único
        # ciclo materializado.
        # ======================================================

        if (
            fecha_inicio
            and fecha_fin
        ):
            actividades = (
                Accion.objects
                .filter(
                    plan__in=(
                        visible_plans
                    ),
                    periodicidad__in=[
                        PERIODICIDAD_SEMANAL,
                        PERIODICIDAD_QUINCENAL,
                        PERIODICIDAD_MENSUAL,
                        PERIODICIDAD_BIMESTRAL,
                        PERIODICIDAD_TRIMESTRAL,
                        PERIODICIDAD_ANUAL,
                    ],
                )
                .select_related(
                    "plan",
                    "responsable",
                    "responsable__profile",
                    "responsable__profile__unidad_organizacional",
                )
            )

            for actividad in actividades:
                fechas = (
                    actividad
                    .fechas_programadas_en_rango(
                        fecha_inicio,
                        fecha_fin,
                    )
                )

                ambitos = (
                    actividad.ambitos
                    or [
                        "JL"
                    ]
                )

                descripcion = (
                    strip_tags(
                        actividad.accion
                        or ""
                    )
                    .strip()
                )

                if not descripcion:
                    descripcion = (
                        f"Actividad "
                        f"{actividad.pk}"
                    )

                responsable_normativo = (
                    responsable_normativo_display(
                        actividad
                    )
                )

                for ambito in ambitos:
                    responsable = (
                        actividad
                        .resolver_responsable_ejecucion(
                            ambito
                        )
                    )

                    es_operativamente_visible = (
                        responsable
                        is not None
                        and responsable.pk
                        in responsables_ids
                    )

                    es_normativamente_visible = (
                        bool(
                            actividad
                            .puesto_responsable
                        )
                        and (
                            actividad
                            .puesto_responsable
                            in claves_normativas
                        )
                    )

                    if (
                        not es_operativamente_visible
                        and not es_normativamente_visible
                    ):
                        continue

                    responsable_operativo = (
                        nombre_calendario(
                            responsable
                        )
                    )

                    unidad_operativa = (
                        unidad_operativa_display(
                            responsable
                        )
                    )

                    es_mia = (
                        responsable
                        is not None
                        and responsable.pk
                        == request.user.id
                    )

                    for fecha in fechas:
                        clave = (
                            actividad.pk,
                            ambito,
                            fecha,
                        )

                        if (
                            clave
                            in eventos_existentes
                        ):
                            continue

                        # --------------------------------------
                        # Estado de la proyección
                        # --------------------------------------

                        if fecha > hoy:
                            estado = (
                                "programada"
                            )

                            estado_display = (
                                "Programada"
                            )

                        elif fecha == hoy:
                            estado = (
                                "vence_hoy"
                            )

                            estado_display = (
                                "Vence hoy"
                            )

                        else:
                            estado = (
                                "pendiente"
                            )

                            estado_display = (
                                "Pendiente"
                            )

                        # --------------------------------------
                        # Título
                        # --------------------------------------

                        if es_supervisor_agenda:

                            if es_mia:
                                titulo = (
                                    f"YO — "
                                    f"{descripcion}"
                                )

                            elif responsable_operativo:
                                titulo = (
                                    f"{responsable_operativo} "
                                    f"— {descripcion}"
                                )

                            elif responsable_normativo:
                                titulo = (
                                    f"{responsable_normativo} "
                                    f"— {descripcion}"
                                )

                            else:
                                titulo = (
                                    descripcion
                                )

                        else:
                            titulo = (
                                descripcion
                            )

                        # --------------------------------------
                        # Evidencia
                        # --------------------------------------

                        if (
                            actividad
                            .formato_evidencia
                            == FORMATO_SIN_EVIDENCIA
                        ):
                            evidencia = (
                                "No requerida"
                            )

                        else:
                            evidencia = (
                                "Pendiente"
                            )

                        eventos.append(
                            {
                                "id": (
                                    "proyectada-"
                                    f"{actividad.pk}-"
                                    f"{ambito}-"
                                    f"{fecha.isoformat()}"
                                ),
                                "title": titulo,
                                "start": (
                                    fecha.isoformat()
                                ),
                                "allDay": True,
                                "extendedProps": {
                                    "activityId": (
                                        actividad.pk
                                    ),
                                    "planId": (
                                        actividad
                                        .plan
                                        .pk
                                    ),
                                    "plan": (
                                        actividad
                                        .plan
                                        .nombre
                                    ),
                                    "planUrl": reverse(
                                        "pas:detalle",
                                        args=[
                                            actividad
                                            .plan
                                            .pk
                                        ],
                                    ),
                                    "activityDetailUrl": reverse(
                                        "pas:activity-detail",
                                        args=[
                                            actividad.pk
                                        ],
                                    ),
                                    "folio": (
                                        actividad
                                        .plan
                                        .folio
                                        or ""
                                    ),
                                    "ciclo": (
                                        "Proyección"
                                    ),
                                    "ambito": (
                                        dict(
                                            AMBITO
                                        )
                                        .get(
                                            ambito,
                                            ambito,
                                        )
                                    ),
                                    "responsable": (
                                        responsable_operativo
                                    ),
                                    "responsableOperativo": (
                                        responsable_operativo
                                    ),
                                    "responsableNormativo": (
                                        responsable_normativo
                                    ),
                                    "unidadOperativa": (
                                        unidad_operativa
                                    ),
                                    "visiblePorOperacion": (
                                        es_operativamente_visible
                                    ),
                                    "visiblePorNormativa": (
                                        es_normativamente_visible
                                    ),
                                    "estado": estado,
                                    "estadoDisplay": (
                                        estado_display
                                    ),
                                    "evidencia": (
                                        evidencia
                                    ),
                                    "completada": False,
                                    "esMia": es_mia,
                                    "proyectada": True,
                                    "continua": False,
                                },
                            }
                        )

        eventos.sort(
            key=lambda evento: (
                evento[
                    "start"
                ],
                evento[
                    "title"
                ],
            )
        )

        return JsonResponse(
            eventos,
            safe=False,
        )


class PASAdd(PermissionRequiredMixin, CreateView):
    permission_required = "pas.add_plan"
    model = Plan
    form_class = PlanForm
    template_name = "pas/add.html"

    def dispatch(self, request, *args, **kwargs):
        if request.headers.get("HX-Request") and request.GET.get("close"):
            return HttpResponse("")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_action": reverse("pas:add"),
                "hx_target": "#pas-form-container",
                "hx_swap": "innerHTML",
                "form_in_modal": False,
            }
        )
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["pas/partials/_plan_form.html"]
        return super().get_template_names()

    def get_success_url(self):
        return reverse("pas:detalle", args=[self.object.pk])

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            redirect_url = str(self.get_success_url())
            return HttpResponse("", status=204, headers={"HX-Redirect": redirect_url})
        return response

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request"):
            return self.render_to_response(self.get_context_data(form=form), status=422)
        return super().form_invalid(form)


class PASDetail(DetailView):
    model = Plan
    template_name = "pas/plan_detail.html"

    def get_queryset(self):
        return Plan.objects.visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plan"] = self.object
        return context


@method_decorator(
    login_required,
    name="dispatch",
)
class PlanSourceDocumentView(
    View
):
    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        visible_plans = (
            Plan.objects.visible_to(
                request.user
            )
        )

        plan = get_object_or_404(
            visible_plans,
            pk=kwargs["pk"],
        )

        if not plan.documento_fuente:
            raise Http404(
                "El plan no tiene documento fuente."
            )

        try:
            archivo = (
                plan.documento_fuente
                .open("rb")
            )
        except FileNotFoundError:
            raise Http404(
                "No se encontró el documento fuente."
            )

        nombre = (
            plan.documento_fuente.name
            .rsplit("/", 1)[-1]
        )

        return FileResponse(
            archivo,
            as_attachment=False,
            filename=nombre,
        )


class PlanSummaryView(DetailView):
    model = Plan
    template_name = "pas/partials/_plan_summary.html"

    def get_queryset(self):
        return Plan.objects.visible_to(
            self.request.user
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        plan = self.object

        activities = list(
            plan.accion_set
            .select_related(
                "responsable"
            )
            .prefetch_related(
                "ciclos__ejecuciones"
            )
            .order_by(
                "id"
            )
        )

        total_activities = len(
            activities
        )

        # ======================================================
        # El avance global sólo tiene sentido cuando el plan
        # tiene un horizonte finito.
        # ======================================================

        tiene_avance = bool(
            plan.fecha_termino
        )

        total_ejecuciones = 0
        ejecuciones_terminadas = 0
        ejecuciones_pendientes = 0

        progress = None

        all_closed = False

        # ======================================================
        # Plan finito
        # ======================================================

        if tiene_avance:
            # --------------------------------------------------
            # Materializamos todas las ejecuciones que deben
            # existir dentro del horizonte temporal del plan.
            # --------------------------------------------------

            for activity in activities:
                if (
                    activity.periodicidad
                    == PERIODICIDAD_MANUAL
                ):
                    continue

                activity.generar_ejecuciones()

            # --------------------------------------------------
            # Universo real de ejecuciones del plan.
            # --------------------------------------------------

            executions = (
                Ejecucion.objects.filter(
                    ciclo__accion__plan=plan,
                    ciclo__fecha_fin__lte=(
                        plan.fecha_termino
                    ),
                )
            )

            if plan.fecha_inicio:
                executions = (
                    executions.filter(
                        ciclo__fecha_inicio__gte=(
                            plan.fecha_inicio
                        )
                    )
                )

            total_ejecuciones = (
                executions.count()
            )

            ejecuciones_terminadas = (
                executions.filter(
                    completada=True
                ).count()
            )

            ejecuciones_pendientes = (
                total_ejecuciones
                - ejecuciones_terminadas
            )

            # --------------------------------------------------
            # Avance
            # --------------------------------------------------

            if total_ejecuciones:
                progress = round(
                    (
                        ejecuciones_terminadas
                        / total_ejecuciones
                    )
                    * 100
                )

            else:
                progress = 0

            # --------------------------------------------------
            # Cierre operativo del universo programado.
            # --------------------------------------------------

            all_closed = (
                total_ejecuciones > 0
                and ejecuciones_pendientes == 0
            )

        # ======================================================
        # Estado de las definiciones de actividad
        # ======================================================

        closed_activities = 0
        open_activities = 0

        for activity in activities:
            if (
                activity.get_estado
                == "Cerrada"
            ):
                closed_activities += 1

            else:
                open_activities += 1

        # ======================================================
        # Contexto
        # ======================================================

        context.update(
            {
                "plan": plan,
                "total_activities": (
                    total_activities
                ),
                "closed_activities": (
                    closed_activities
                ),
                "open_activities": (
                    open_activities
                ),
                "tiene_avance": (
                    tiene_avance
                ),
                "total_ejecuciones": (
                    total_ejecuciones
                ),
                "ejecuciones_terminadas": (
                    ejecuciones_terminadas
                ),
                "ejecuciones_pendientes": (
                    ejecuciones_pendientes
                ),
                "progress": progress,
                "all_closed": (
                    all_closed
                ),
            }
        )

        return context


class PlanActivitiesView(DetailView):
    model = Plan
    template_name = "pas/partials/_activities_list.html"

    def get_queryset(self):
        return Plan.objects.visible_to(
            self.request.user
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        plan = self.object
        hoy = timezone.localdate()

        executions_prefetch = Prefetch(
            "ejecuciones",
            queryset=(
                Ejecucion.objects.select_related(
                    "responsable",
                    "responsable__profile",
                )
                .prefetch_related(
                    "evidencia_registrada",
                )
                .order_by(
                    "ambito",
                )
            ),
        )

        cycles_prefetch = Prefetch(
            "ciclos",
            queryset=(
                CicloActividad.objects.prefetch_related(
                    executions_prefetch,
                ).order_by(
                    "fecha_inicio",
                    "numero",
                )
            ),
        )

        activities_queryset = (
            plan.accion_set.select_related(
                "responsable",
                "responsable__profile",
            )
            .prefetch_related(
                cycles_prefetch,
            )
            .order_by(
                "fecha_fin",
                "id",
            )
        )

        def state_priority(
            estado,
        ):
            if estado == "Abierta Fuera de Tiempo":
                return 0

            if estado == "Abierta en Tiempo":
                return 2

            if estado == "Cerrada":
                return 3

            return 1

        def build_estado_badge(
            estado,
            closed_in_time,
        ):
            if estado == "Abierta Fuera de Tiempo":
                return {
                    "classes": ("badge-error text-error-content"),
                    "text": "Abierta",
                    "title": "Abierta fuera de tiempo",
                }

            if estado == "Abierta en Tiempo":
                return {
                    "classes": (
                        "badge-outline "
                        "border border-warning "
                        "text-base-content "
                        "bg-transparent"
                    ),
                    "text": "Abierta",
                    "title": "Abierta en tiempo",
                }

            if estado == "Cerrada":
                if closed_in_time is False:
                    return {
                        "classes": ("badge-success badge-outline text-success"),
                        "text": "Cerrada",
                        "title": "Cerrada fuera de tiempo",
                    }

                return {
                    "classes": ("badge-success text-success-content"),
                    "text": "Cerrada",
                    "title": "Cerrada en tiempo",
                }

            return {
                "classes": ("badge-neutral badge-outline"),
                "text": (estado or "Sin estado"),
                "title": (estado or "Sin estado"),
            }

        def ciclo_pendiente(
            cycles,
        ):
            for cycle in cycles:
                executions = list(cycle.ejecuciones.all())

                if not executions:
                    continue

                if any(not execution.completada for execution in executions):
                    return cycle

            return None

        def ciclo_referencia(
            cycles,
        ):
            pending = ciclo_pendiente(cycles)

            if pending:
                return pending

            if cycles:
                return cycles[-1]

            return None

        def descripcion_corta(
            activity,
        ):
            texto = strip_tags(activity.accion or "")

            texto = " ".join(texto.split())

            limite = 125

            if len(texto) <= limite:
                return texto

            return texto[:limite].rstrip() + "…"

        def nombre_compacto(
            usuario,
        ):
            if not usuario:
                return "—"

            try:
                profile = usuario.profile

                if profile and profile.nombre_calendario:
                    return profile.nombre_calendario

            except Exception:
                pass

            nombre = usuario.get_full_name() or usuario.username

            return nombre[:10]

        def responsables_ciclo(
            cycle,
        ):
            if not cycle:
                return []

            nombres = []

            for execution in cycle.ejecuciones.all():
                nombre = nombre_compacto(execution.responsable)

                if nombre != "—" and nombre not in nombres:
                    nombres.append(nombre)

            return nombres

        activities = []

        for activity in activities_queryset:
            estado = activity.get_estado

            cycles = list(activity.ciclos.all())

            pending_cycle = ciclo_pendiente(cycles)

            reference_cycle = ciclo_referencia(cycles)

            all_executions = []

            for cycle in cycles:
                all_executions.extend(list(cycle.ejecuciones.all()))

            execution_summary = []

            if reference_cycle:
                for execution in reference_cycle.ejecuciones.all():
                    execution_summary.append(
                        {
                            "execution": execution,
                            "ambito": (execution.ambito),
                            "ambito_display": (execution.get_ambito_display()),
                            "tiene_evidencia": (execution.tiene_evidencia),
                            "estado": (execution.estado_agenda),
                        }
                    )

            # ==================================================
            # Cierre en tiempo
            #
            # Ya no depende de Seguimiento.
            #
            # Si todas las ejecuciones están cerradas,
            # se considera fuera de tiempo cuando alguna
            # fue cerrada después de su fecha de término.
            # ==================================================

            closed_in_time = None

            if estado == "Cerrada" and all_executions:
                closed_in_time = not any(
                    (
                        execution.fecha_completada
                        and execution.fecha_completada > execution.fecha_fin
                    )
                    for execution in all_executions
                )

            nombres_responsables = responsables_ciclo(pending_cycle or reference_cycle)

            if nombres_responsables:
                responsable_compacto = ", ".join(nombres_responsables)

            elif activity.responsable_id:
                responsable_compacto = nombre_compacto(activity.responsable)

            else:
                responsable_compacto = "—"

            responsable_normativo = "—"

            if activity.puesto_responsable:
                unidad_normativa = UnidadOrganizacional.objects.filter(
                    clave=(activity.puesto_responsable)
                ).first()

                if unidad_normativa:
                    responsable_normativo = unidad_normativa.etiqueta_funcional

                else:
                    responsable_normativo = activity.puesto_responsable

            activities.append(
                {
                    "activity": activity,
                    "descripcion_corta": (descripcion_corta(activity)),
                    "responsable_normativo": (responsable_normativo),
                    "responsable_compacto": (responsable_compacto),
                    "estado": estado,
                    "estado_priority": (state_priority(estado)),
                    "closed_in_time": (closed_in_time),
                    "badge": (
                        build_estado_badge(
                            estado,
                            closed_in_time,
                        )
                    ),
                    "reference_cycle": (reference_cycle),
                    "proxima_accion": (pending_cycle),
                    "execution_summary": (execution_summary),
                    "execution_total": (len(execution_summary)),
                    "execution_with_evidence": (
                        sum(1 for item in execution_summary if item["tiene_evidencia"])
                    ),
                }
            )

        activities.sort(
            key=lambda item: (
                item["estado_priority"],
                (
                    item["proxima_accion"].fecha_fin
                    if item["proxima_accion"]
                    else date.max
                ),
                item["activity"].pk,
            )
        )

        context.update(
            {
                "plan": plan,
                "activities": activities,
                "can_modify": (plan.permite_modificaciones),
                "hoy": hoy,
            }
        )

        return context



class PlanFormMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_action": self.request.path,
                "hx_target": "#pas-modal-content",
                "hx_swap": "innerHTML",
                "form_in_modal": True,
                "modal_id": "pas-modal",
            }
        )
        return context

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request"):
            return self.render_to_response(self.get_context_data(form=form), status=422)
        return super().form_invalid(form)


class PlanUpdateView(
    PermissionRequiredMixin,
    PlanFormMixin,
    UpdateView,
):
    permission_required = "pas.change_plan"
    model = Plan
    form_class = PlanForm
    template_name = "pas/partials/_plan_form.html"

    def get_queryset(self):
        return Plan.objects.visible_to(
            self.request.user
        )

    def get_success_url(self):
        return reverse(
            "pas:detalle",
            args=[
                self.object.pk,
            ],
        )

    def form_valid(self, form):
        response = super().form_valid(
            form
        )

        if self.request.headers.get(
            "HX-Request"
        ):
            header = hx_trigger_header(
                "pas:refresh-summary",
                "pas:close-modal",
            )

            return HttpResponse(
                "",
                status=204,
                headers={
                    "HX-Trigger": header,
                },
            )

        return response


class PlanClosureView(
    PermissionRequiredMixin,
    FormView,
):
    permission_required = "pas.change_plan"
    form_class = PlanClosureForm
    template_name = (
        "pas/partials/"
        "_plan_closure_form.html"
    )

    def dispatch(
        self,
        request,
        *args,
        **kwargs,
    ):
        visible_plans = (
            Plan.objects.visible_to(
                request.user
            )
        )

        self.plan = get_object_or_404(
            visible_plans,
            pk=kwargs["pk"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        context.update(
            {
                "plan": self.plan,
                "form_action": self.request.path,
                "modal_id": "pas-modal",
            }
        )

        return context

    def get_initial(self):
        initial = super().get_initial()

        if self.plan.eliminacion:
            initial["resultado"] = "close"
            initial["comentarios"] = (
                self.plan.txt_eliminacion
            )

        elif self.plan.recurrencia:
            initial["resultado"] = (
                "recurrence"
            )
            initial["comentarios"] = (
                self.plan.txt_recurrencia
            )

        return initial

    def form_invalid(
        self,
        form,
    ):
        if self.request.headers.get(
            "HX-Request"
        ):
            return self.render_to_response(
                self.get_context_data(
                    form=form
                ),
                status=422,
            )

        return super().form_invalid(
            form
        )

    def form_valid(
        self,
        form,
    ):
        resultado = (
            form.cleaned_data[
                "resultado"
            ]
        )

        comentarios = (
            form.cleaned_data.get(
                "comentarios"
            )
        )

        if resultado == "close":
            self.plan.eliminacion = True
            self.plan.txt_eliminacion = (
                comentarios
            )
            self.plan.recurrencia = False
            self.plan.txt_recurrencia = ""

        else:
            self.plan.recurrencia = True
            self.plan.txt_recurrencia = (
                comentarios
            )
            self.plan.eliminacion = False
            self.plan.txt_eliminacion = ""

        self.plan.save(
            update_fields=[
                "eliminacion",
                "txt_eliminacion",
                "recurrencia",
                "txt_recurrencia",
            ]
        )

        if self.request.headers.get(
            "HX-Request"
        ):
            header = hx_trigger_header(
                "pas:refresh-summary",
                "pas:close-modal",
            )

            return HttpResponse(
                "",
                status=204,
                headers={
                    "HX-Trigger": header,
                },
            )

        return super().form_valid(
            form
        )

    def get_success_url(self):
        return reverse(
            "pas:detalle",
            args=[
                self.plan.pk,
            ],
        )


class ActivityBaseView:
    form_class = AccionForm
    template_name = "pas/partials/_activity_form.html"

    def get_success_url(self):
        return reverse("pas:detalle", args=[self.plan.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "plan": self.plan,
                "form_action": self.request.path,
                "modal_id": "pas-modal",
            }
        )
        return context

    def form_invalid(
        self,
        form,
    ):
        if self.request.headers.get("HX-Request"):
            return self.render_to_response(
                self.get_context_data(form=form),
                status=200,
            )

        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.object.periodicidad != PERIODICIDAD_MANUAL:
            self.object.generar_ejecuciones()

        if self.request.headers.get("HX-Request"):
            header = hx_trigger_header(
                "pas:refresh-activities",
                "pas:refresh-summary",
                "pas:close-modal",
            )

            return HttpResponse(
                "",
                status=204,
                headers={
                    "HX-Trigger": header,
                },
            )

        return response

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        if not self.plan.permite_modificaciones:
            return HttpResponse(
                "El plan se encuentra cerrado o con recurrencia registrada.",
                status=409,
            )

        return response


class ActivityCreateView(
    PermissionRequiredMixin,
    ActivityBaseView,
    CreateView,
):
    permission_required = "pas.add_accion"
    model = Accion

    def dispatch(
        self,
        request,
        *args,
        **kwargs,
    ):
        visible_plans = (
            Plan.objects.visible_to(
                request.user
            )
        )

        self.plan = get_object_or_404(
            visible_plans,
            pk=kwargs["pk"],
        )

        if not self.plan.permite_modificaciones:
            return HttpResponse(
                (
                    "El plan se encuentra cerrado "
                    "o con recurrencia registrada."
                ),
                status=409,
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def form_valid(
        self,
        form,
    ):
        form.instance.plan = self.plan
        form.instance.user = (
            self.request.user
        )

        return super().form_valid(
            form
        )


class ActivityUpdateView(
    PermissionRequiredMixin,
    ActivityBaseView,
    UpdateView,
):
    permission_required = (
        "pas.change_accion"
    )

    model = Accion

    def get_queryset(self):
        visible_plans = (
            Plan.objects.visible_to(
                self.request.user
            )
        )

        return (
            Accion.objects
            .filter(
                plan__in=visible_plans
            )
            .select_related(
                "plan"
            )
        )

    def get_object(
        self,
        queryset=None,
    ):
        obj = super().get_object(
            queryset
        )

        self.plan = obj.plan

        if not (
            self.plan.permite_modificaciones
        ):
            from django.core.exceptions import (
                PermissionDenied,
            )

            raise PermissionDenied(
                (
                    "El plan se encuentra cerrado "
                    "o con recurrencia registrada."
                )
            )

        return obj


class ActivityDeleteView(
    PermissionRequiredMixin,
    DeleteView,
):
    permission_required = (
        "pas.delete_accion"
    )

    model = Accion

    template_name = (
        "pas/partials/"
        "_confirm_delete.html"
    )

    def get_queryset(
        self,
    ):
        visible_plans = (
            Plan.objects.visible_to(
                self.request.user
            )
        )

        return (
            Accion.objects
            .filter(
                plan__in=visible_plans
            )
            .select_related(
                "plan"
            )
        )

    def get_success_url(
        self,
    ):
        return reverse(
            "pas:detalle",
            args=[
                self.object.plan.pk
            ],
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = (
            super()
            .get_context_data(
                **kwargs
            )
        )

        context.update(
            {
                "activity": (
                    self.object
                ),
                "form_action": (
                    self.request.path
                ),
                "modal_id": (
                    "pas-modal"
                ),
            }
        )

        return context

    def get_object(
        self,
        queryset=None,
    ):
        obj = super().get_object(
            queryset
        )

        if not (
            obj.plan
            .permite_modificaciones
        ):
            from django.core.exceptions import (
                PermissionDenied,
            )

            raise PermissionDenied(
                (
                    "El plan se encuentra "
                    "cerrado o no admite "
                    "modificaciones."
                )
            )

        return obj

    def form_valid(
        self,
        form,
    ):
        self.object = (
            self.get_object()
        )

        success_url = (
            self.get_success_url()
        )

        self.object.delete()

        if self.request.headers.get(
            "HX-Request"
        ):
            header = (
                hx_trigger_header(
                    "pas:refresh-activities",
                    "pas:refresh-summary",
                    "pas:close-modal",
                )
            )

            return HttpResponse(
                "",
                status=204,
                headers={
                    "HX-Trigger": (
                        header
                    ),
                },
            )

        return HttpResponse(
            status=302,
            headers={
                "Location": (
                    success_url
                ),
            },
        )


class EvidenceDownloadView(
    DetailView
):
    model = Evidencia

    def get_queryset(self):
        visible_plans = (
            Plan.objects.visible_to(
                self.request.user
            )
        )

        return (
            Evidencia.objects
            .filter(
                Q(
                    ejecucion__ciclo__accion__plan__in=(
                        visible_plans
                    )
                )
                |
                Q(
                    accion__plan__in=(
                        visible_plans
                    )
                )
            )
            .select_related(
                "accion",
                "accion__plan",
                "ejecucion",
                "ejecucion__ciclo",
                "ejecucion__ciclo__accion",
                "ejecucion__ciclo__accion__plan",
            )
        )

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        evidence = self.get_object()

        if not evidence.archivo:
            raise Http404(
                "La evidencia no tiene archivo."
            )

        return FileResponse(
            evidence.archivo.open(
                "rb"
            ),
            as_attachment=False,
            filename=(
                evidence.archivo.name
                .rsplit("/", 1)[-1]
            ),
        )


class ExecutionEvidenceBaseView(CreateView):
    model = Evidencia
    form_class = EvidenciaForm
    template_name = "pas/partials/_evidence_form.html"

    def dispatch(
        self,
        request,
        *args,
        **kwargs,
    ):
        visible_plans = Plan.objects.visible_to(request.user)

        self.execution = get_object_or_404(
            Ejecucion.objects.select_related(
                "ciclo",
                "ciclo__accion",
                "ciclo__accion__plan",
                "ciclo__accion__plan__user",
                "responsable",
            ).filter(
                ciclo__accion__plan__in=(visible_plans),
            ),
            pk=kwargs["pk"],
        )

        if not usuario_puede_gestionar_ejecucion(
            request.user,
            self.execution,
        ):
            return HttpResponse(
                ("No tienes permiso para registrar evidencia en esta ejecución."),
                status=403,
            )

        if self.execution.accion.formato_evidencia == FORMATO_SIN_EVIDENCIA:
            return HttpResponse(
                ("Esta actividad no requiere evidencia documental."),
                status=409,
            )

        if not (self.execution.plan.permite_modificaciones):
            return HttpResponse(
                ("El plan se encuentra cerrado o no admite modificaciones."),
                status=409,
            )

        if Evidencia.objects.filter(ejecucion=self.execution).exists():
            return HttpResponse(
                ("Esta ejecución ya tiene una evidencia registrada."),
                status=409,
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_success_url(self):
        return reverse(
            "pas:detalle",
            args=[
                self.execution.plan.pk,
            ],
        )

    def get_initial(self):
        initial = super().get_initial()

        initial.setdefault(
            "fecha",
            timezone.localdate(),
        )

        return initial

    def get_context_data(
        self,
        **kwargs,
    ):
        context = (
            super().get_context_data(
                **kwargs
            )
        )

        context.update(
            {
                "execution": (
                    self.execution
                ),
                "activity": (
                    self.execution.accion
                ),
                "form_action": (
                    self.request.path
                ),
                "modal_id": "pas-modal",
            }
        )

        return context

    def form_invalid(self, form):
        if self.request.headers.get(
            "HX-Request"
        ):
            return self.render_to_response(
                self.get_context_data(
                    form=form
                ),
                status=422,
            )

        return super().form_invalid(
            form
        )

    def form_valid(self, form):
        form.instance.ejecucion = (
            self.execution
        )

        form.instance.accion = None

        form.instance.user = (
            self.request.user
        )

        response = super().form_valid(
            form
        )

        if self.request.headers.get("HX-Request"):
            header = hx_trigger_header(
                "pas:refresh-activity",
                "pas:refresh-activities",
                "pas:refresh-summary",
                "pas:refresh-agenda",
            )

            return HttpResponse(
                "",
                status=204,
                headers={
                    "HX-Trigger": header,
                },
            )

        return response


class ExecutionEvidenceCreateView(
    PermissionRequiredMixin,
    ExecutionEvidenceBaseView,
):
    permission_required = "pas.add_evidencia"


class ExecutionEvidenceDetailView(
    DetailView
):
    model = Ejecucion
    template_name = (
        "pas/partials/"
        "_execution_evidence_detail.html"
    )

    def get_queryset(self):
        visible_plans = (
            Plan.objects.visible_to(
                self.request.user
            )
        )

        return (
            Ejecucion.objects
            .filter(
                ciclo__accion__plan__in=(
                    visible_plans
                )
            )
            .select_related(
                "ciclo",
                "ciclo__accion",
                "ciclo__accion__plan",
                "responsable",
            )
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = (
            super().get_context_data(
                **kwargs
            )
        )

        execution = self.object

        try:
            evidence = (
                execution
                .evidencia_registrada
            )
        except Evidencia.DoesNotExist:
            evidence = None

        context.update(
            {
                "execution": execution,
                "activity": (
                    execution.accion
                ),
                "evidence": evidence,
            }
        )

        return context


@method_decorator(
    login_required,
    name="dispatch",
)
class ExecutionCompleteView(View):
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        visible_plans = (
            Plan.objects.visible_to(
                request.user
            )
        )

        execution = get_object_or_404(
            Ejecucion.objects
            .select_related(
                "ciclo",
                "ciclo__accion",
                "ciclo__accion__plan",
                "ciclo__accion__plan__user",
                "responsable",
            )
            .filter(
                ciclo__accion__plan__in=(
                    visible_plans
                )
            ),
            pk=kwargs["pk"],
        )

        if not usuario_puede_gestionar_ejecucion(
            request.user,
            execution,
        ):
            return HttpResponse(
                (
                    "No tienes permiso para "
                    "cerrar o reabrir esta ejecución."
                ),
                status=403,
            )

        if not (
            execution.plan
            .permite_modificaciones
        ):
            return HttpResponse(
                (
                    "El plan se encuentra cerrado "
                    "o no admite modificaciones."
                ),
                status=409,
            )

        action = request.POST.get(
            "action",
            "complete",
        )

        if action == "reopen":
            execution.reabrir()

        else:
            execution.marcar_completada()

        if request.headers.get(
            "HX-Request"
        ):
            header = hx_trigger_header(
                "pas:refresh-activity",
                "pas:refresh-activities",
                "pas:refresh-summary",
                "pas:refresh-agenda",
            )

            return HttpResponse(
                "",
                status=204,
                headers={
                    "HX-Trigger": header,
                },
            )

        return HttpResponse(
            status=204
        )


@method_decorator(
    login_required,
    name="dispatch",
)
class ActivityDetailView(
    DetailView
):
    model = Accion
    template_name = (
        "pas/partials/"
        "_activity_detail.html"
    )

    def get_queryset(
        self,
    ):
        visible_plans = (
            Plan.objects.visible_to(
                self.request.user
            )
        )

        return (
            Accion.objects
            .filter(
                plan__in=visible_plans
            )
            .select_related(
                "plan",
                "responsable",
                "responsable__profile",
                "responsable__profile__unidad_organizacional",
            )
            .prefetch_related(
                "ciclos__ejecuciones__responsable",
                "ciclos__ejecuciones__responsable__profile",
                "ciclos__ejecuciones__evidencia_registrada",
            )
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        activity = self.object

        ciclos = list(
            activity.ciclos.all().order_by(
                "fecha_inicio",
                "numero",
            )
        )

        ejecuciones = []

        for ciclo in ciclos:
            for ejecucion in ciclo.ejecuciones.all().order_by(
                "ambito",
                "pk",
            ):
                ejecucion.puede_gestionar = usuario_puede_gestionar_ejecucion(
                    self.request.user,
                    ejecucion,
                )

                ejecuciones.append(ejecucion)

        unidad_normativa = None

        if activity.puesto_responsable:
            unidad_normativa = UnidadOrganizacional.objects.filter(
                clave=(activity.puesto_responsable)
            ).first()

        responsable_normativo = (
            unidad_normativa.etiqueta_funcional
            if unidad_normativa
            else (activity.puesto_responsable or "—")
        )

        responsable_operativo = "—"

        if activity.responsable:
            perfil_operativo = getattr(
                activity.responsable,
                "profile",
                None,
            )

            if perfil_operativo:
                responsable_operativo = perfil_operativo.nombre_calendario
            else:
                responsable_operativo = (
                    activity.responsable.get_full_name()
                    or activity.responsable.username
                )

        ejecuciones_pendientes = [
            ejecucion for ejecucion in ejecuciones if not ejecucion.completada
        ]

        proxima_ejecucion = None

        if ejecuciones_pendientes:
            proxima_ejecucion = sorted(
                ejecuciones_pendientes,
                key=lambda ejecucion: (
                    ejecucion.fecha_fin,
                    ejecucion.fecha_inicio,
                    ejecucion.pk,
                ),
            )[0]

        context.update(
            {
                "activity": activity,
                "today": timezone.localdate(),
                "plan": activity.plan,
                "ciclos": ciclos,
                "ejecuciones": ejecuciones,
                "responsable_normativo": (responsable_normativo),
                "responsable_operativo": (responsable_operativo),
                "proxima_ejecucion": (proxima_ejecucion),
                "can_modify": (activity.plan.permite_modificaciones),
            }
        )

        return context

