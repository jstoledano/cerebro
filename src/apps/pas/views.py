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
from .forms import PlanForm, AccionForm, SeguimientoForm, PlanClosureForm, EvidenciaForm
from .models import (
    Plan,
    Accion,
    Seguimiento,
    Evidencia,
    CicloActividad,
    Ejecucion,
    AMBITO,
    CERRADA,
    PERIODICIDAD_UNICA,
    PERIODICIDAD_MANUAL,
    FORMATO_SIN_EVIDENCIA,
    PERIODICIDAD_SEMANAL,
    PERIODICIDAD_QUINCENAL,
    PERIODICIDAD_MENSUAL,
    PERIODICIDAD_BIMESTRAL,
    PERIODICIDAD_TRIMESTRAL,
    PRIORIDAD_URGENTE,
    PRIORIDAD_CRITICA,
)


def hx_trigger_header(*events):
    if not events:
        return ""
    payload = {event: "" for event in events}
    return json.dumps(payload)


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
        context = super().get_context_data(
            **kwargs
        )

        followups_prefetch = Prefetch(
            "seguimiento_set",
            queryset=(
                Seguimiento.objects
                .select_related(
                    "responsable"
                )
                .order_by(
                    "-fecha",
                    "-created",
                )
            ),
        )

        plan_actions_prefetch = Prefetch(
            "accion_set",
            queryset=(
                Accion.objects
                .select_related(
                    "responsable"
                )
                .prefetch_related(
                    followups_prefetch
                )
            ),
            to_attr="pas_actions",
        )

        plan_list = (
            Plan.objects
            .visible_to(
                self.request.user
            )
            .prefetch_related(
                plan_actions_prefetch
            )
            .order_by(
                "-fecha_llenado"
            )
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
            Accion.objects
            .filter(
                plan__in=plan_list
            )
            .select_related(
                "plan",
                "responsable",
            )
            .prefetch_related(
                followups_prefetch
            )
        )

        for action in action_qs:
            estado = action.get_estado

            if estado == "Cerrada":
                continue

            priority = state_priority(
                estado
            )

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

        action_list = [
            item[3]
            for item in action_items
        ]

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

            plan.abiertas_en_tiempo = (
                abiertas_en_tiempo
            )

            plan.abiertas_fuera_de_tiempo = (
                abiertas_fuera_de_tiempo
            )

            plan.total_actividades = (
                cerradas
                + abiertas_en_tiempo
                + abiertas_fuera_de_tiempo
            )

        context[
            "plan_list"
        ] = plan_list

        context[
            "action_list"
        ] = action_list

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
        context = super().get_context_data(
            **kwargs
        )

        hoy = timezone.localdate()

        inicio_semana = (
            hoy
            - datetime.timedelta(
                days=hoy.weekday()
            )
        )

        fin_semana = (
            inicio_semana
            + datetime.timedelta(
                days=6
            )
        )

        visible_plans = (
            Plan.objects.visible_to(
                self.request.user
            )
        )

        actividades_recurrentes_abiertas = (
            Accion.objects
            .filter(
                plan__in=visible_plans,
                fecha_fin__isnull=True,
            )
            .exclude(
                periodicidad__in=[
                    PERIODICIDAD_UNICA,
                    PERIODICIDAD_MANUAL,
                ]
            )
            .select_related(
                "plan",
                "responsable",
            )
        )

        for actividad in (
            actividades_recurrentes_abiertas
        ):
            actividad.generar_ejecuciones()

        queryset_ejecuciones = (
            Ejecucion.objects
            .filter(
                ciclo__accion__plan__in=(
                    visible_plans
                ),
            )
            .select_related(
                "ciclo",
                "ciclo__accion",
                "ciclo__accion__plan",
                "responsable",
                "responsable__profile",
                "responsable__profile__unidad_organizacional",
            )
            .prefetch_related(
                "evidencia_registrada",
            )
            .order_by(
                "ciclo__fecha_fin",
                "ciclo__fecha_inicio",
                "ciclo__accion_id",
            )
        )

        def clasificar_atencion(
            ejecuciones,
        ):
            """
            Clasifica cada ejecución pendiente en un único
            nivel de atención.

            Jerarquía:

            1. Urgente
               - vencida
               - vence hoy

            2. Requiere atención
               - vence después de hoy y hasta el domingo
               - prioridad urgente/crítica actualmente
                 en ejecución

            3. Vigilar
               - inicia hoy
               - inicia después de hoy y hasta el domingo

            Las ejecuciones posteriores al horizonte semanal
            no aparecen en la agenda de atención. Permanecen
            disponibles en el calendario.
            """

            urgente = []
            atencion = []
            vigilar = []
            terminadas = []

            vencidas = []
            vencen_hoy = []
            vencen_semana = []
            prioridad_alta = []
            inician_hoy = []
            inician_semana = []

            for ejecucion in ejecuciones:
                if ejecucion.completada:
                    terminadas.append(
                        ejecucion
                    )
                    continue

                fecha_inicio = (
                    ejecucion.fecha_inicio
                )

                fecha_fin = (
                    ejecucion.fecha_fin
                )

                # ------------------------------------------
                # 1. URGENTE
                # ------------------------------------------

                if fecha_fin < hoy:
                    urgente.append(
                        ejecucion
                    )

                    vencidas.append(
                        ejecucion
                    )

                    continue

                if fecha_fin == hoy:
                    urgente.append(
                        ejecucion
                    )

                    vencen_hoy.append(
                        ejecucion
                    )

                    continue

                # ------------------------------------------
                # 2. REQUIERE ATENCIÓN
                # ------------------------------------------

                if (
                    hoy < fecha_fin
                    <= fin_semana
                ):
                    atencion.append(
                        ejecucion
                    )

                    vencen_semana.append(
                        ejecucion
                    )

                    continue

                esta_en_ejecucion = (
                    fecha_inicio
                    <= hoy
                    < fecha_fin
                )

                es_prioridad_alta = (
                    ejecucion.accion.prioridad
                    in {
                        PRIORIDAD_URGENTE,
                        PRIORIDAD_CRITICA,
                    }
                )

                if (
                    esta_en_ejecucion
                    and es_prioridad_alta
                ):
                    atencion.append(
                        ejecucion
                    )

                    prioridad_alta.append(
                        ejecucion
                    )

                    continue

                # ------------------------------------------
                # 3. VIGILAR
                # ------------------------------------------

                if fecha_inicio == hoy:
                    vigilar.append(
                        ejecucion
                    )

                    inician_hoy.append(
                        ejecucion
                    )

                    continue

                if (
                    hoy < fecha_inicio
                    <= fin_semana
                ):
                    vigilar.append(
                        ejecucion
                    )

                    inician_semana.append(
                        ejecucion
                    )

                    continue

            return {
                "urgente": urgente,
                "atencion": atencion,
                "vigilar": vigilar,
                "terminadas": terminadas,

                "vencidas": vencidas,
                "vencen_hoy": vencen_hoy,
                "vencen_semana": vencen_semana,
                "prioridad_alta": prioridad_alta,
                "inician_hoy": inician_hoy,
                "inician_semana": inician_semana,
            }

        # ==================================================
        # AGENDA PERSONAL
        # ==================================================

        ejecuciones_personales = list(
            queryset_ejecuciones.filter(
                responsable=self.request.user
            )
        )

        personal = clasificar_atencion(
            ejecuciones_personales
        )

        # ==================================================
        # SUPERVISIÓN
        # ==================================================

        supervision_activa = False
        unidad_supervision = None
        usuarios_supervisados = []

        perfil = getattr(
            self.request.user,
            "profile",
            None,
        )

        if (
            perfil
            and perfil.unidad_organizacional
        ):
            unidad_supervision = (
                perfil.unidad_organizacional
            )

            usuarios_supervisados = list(
                unidad_supervision
                .obtener_usuarios(
                    incluir_self=False,
                )
            )

            supervision_activa = bool(
                usuarios_supervisados
            )

        supervision = clasificar_atencion(
            []
        )

        if supervision_activa:
            ejecuciones_supervision = list(
                queryset_ejecuciones.filter(
                    responsable__in=(
                        usuarios_supervisados
                    )
                )
            )

            supervision = clasificar_atencion(
                ejecuciones_supervision
            )

        # ==================================================
        # COMPATIBILIDAD TEMPORAL CON EL TEMPLATE ACTUAL
        # ==================================================
        #
        # Estas variables se mantienen mientras cambiamos
        # agenda.html en el siguiente paso.
        #
        # Importante: "pendientes" ya NO significa todo lo
        # incompleto. Sólo contiene elementos dentro del
        # radar de atención.
        # ==================================================

        pendientes_personales = (
            personal["urgente"]
            + personal["atencion"]
            + personal["vigilar"]
        )

        pendientes_supervision = (
            supervision["urgente"]
            + supervision["atencion"]
            + supervision["vigilar"]
        )

        context.update(
            {
                "hoy": hoy,
                "inicio_semana": (
                    inicio_semana
                ),
                "fin_semana": (
                    fin_semana
                ),

                # ==========================================
                # Agenda personal nueva
                # ==========================================

                "urgentes": (
                    personal["urgente"]
                ),

                "requieren_atencion": (
                    personal["atencion"]
                ),

                "vigilar": (
                    personal["vigilar"]
                ),

                "vencidas": (
                    personal["vencidas"]
                ),

                "vencen_hoy": (
                    personal["vencen_hoy"]
                ),

                "vencen_semana": (
                    personal["vencen_semana"]
                ),

                "prioridad_alta": (
                    personal["prioridad_alta"]
                ),

                "inician_hoy": (
                    personal["inician_hoy"]
                ),

                "inician_semana": (
                    personal["inician_semana"]
                ),

                "terminadas": (
                    personal["terminadas"]
                ),

                "total_urgentes": len(
                    personal["urgente"]
                ),

                "total_requieren_atencion": len(
                    personal["atencion"]
                ),

                "total_vigilar": len(
                    personal["vigilar"]
                ),

                "total_vencidas": len(
                    personal["vencidas"]
                ),

                "total_vencen_hoy": len(
                    personal["vencen_hoy"]
                ),

                "total_vencen_semana": len(
                    personal["vencen_semana"]
                ),

                "total_prioridad_alta": len(
                    personal["prioridad_alta"]
                ),

                "total_inician_hoy": len(
                    personal["inician_hoy"]
                ),

                "total_inician_semana": len(
                    personal["inician_semana"]
                ),

                # ==========================================
                # Compatibilidad personal
                # ==========================================

                "pendientes": (
                    pendientes_personales
                ),

                "pendientes_semana": (
                    personal["urgente"]
                    + personal["atencion"]
                ),

                "proximas": (
                    personal["vigilar"]
                ),

                "total_pendientes": len(
                    pendientes_personales
                ),

                "total_pendientes_semana": (
                    len(
                        personal["urgente"]
                    )
                    + len(
                        personal["atencion"]
                    )
                ),

                "total_proximas": len(
                    personal["vigilar"]
                ),

                "total_terminadas": len(
                    personal["terminadas"]
                ),

                # ==========================================
                # Supervisión jerárquica
                # ==========================================

                "supervision_activa": (
                    supervision_activa
                ),

                "unidad_supervision": (
                    unidad_supervision
                ),

                "usuarios_supervisados": (
                    usuarios_supervisados
                ),

                "supervision_urgentes": (
                    supervision["urgente"]
                ),

                "supervision_requieren_atencion": (
                    supervision["atencion"]
                ),

                "supervision_vigilar": (
                    supervision["vigilar"]
                ),

                "supervision_vencidas": (
                    supervision["vencidas"]
                ),

                "supervision_vencen_hoy": (
                    supervision["vencen_hoy"]
                ),

                "supervision_vencen_semana": (
                    supervision["vencen_semana"]
                ),

                "supervision_prioridad_alta": (
                    supervision["prioridad_alta"]
                ),

                "supervision_inician_hoy": (
                    supervision["inician_hoy"]
                ),

                "supervision_inician_semana": (
                    supervision["inician_semana"]
                ),

                "supervision_terminadas": (
                    supervision["terminadas"]
                ),

                "total_supervision_urgentes": len(
                    supervision["urgente"]
                ),

                "total_supervision_requieren_atencion": len(
                    supervision["atencion"]
                ),

                "total_supervision_vigilar": len(
                    supervision["vigilar"]
                ),

                "total_supervision_vencidas": len(
                    supervision["vencidas"]
                ),

                "total_supervision_vencen_hoy": len(
                    supervision["vencen_hoy"]
                ),

                "total_supervision_vencen_semana": len(
                    supervision["vencen_semana"]
                ),

                "total_supervision_prioridad_alta": len(
                    supervision["prioridad_alta"]
                ),

                "total_supervision_inician_hoy": len(
                    supervision["inician_hoy"]
                ),

                "total_supervision_inician_semana": len(
                    supervision["inician_semana"]
                ),

                # ==========================================
                # Compatibilidad supervisión
                # ==========================================

                "supervision_pendientes": (
                    pendientes_supervision
                ),

                "supervision_pendientes_semana": (
                    supervision["urgente"]
                    + supervision["atencion"]
                ),

                "supervision_proximas": (
                    supervision["vigilar"]
                ),

                "total_supervision_pendientes": len(
                    pendientes_supervision
                ),

                "total_supervision_pendientes_semana": (
                    len(
                        supervision["urgente"]
                    )
                    + len(
                        supervision["atencion"]
                    )
                ),

                "total_supervision_proximas": len(
                    supervision["vigilar"]
                ),

                "total_supervision_terminadas": len(
                    supervision["terminadas"]
                ),
            }
        )

        return context


@method_decorator(
    login_required,
    name="dispatch",
)
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

        modo = request.GET.get(
            "mode",
            "personal",
        )

        if modo not in {
            "personal",
            "supervision",
        }:
            return JsonResponse(
                {
                    "error": (
                        "El modo de calendario "
                        "no es válido."
                    )
                },
                status=400,
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

        responsables = [
            request.user
        ]

        if modo == "supervision":
            perfil = getattr(
                request.user,
                "profile",
                None,
            )

            if (
                not perfil
                or not perfil.unidad_organizacional
            ):
                return JsonResponse(
                    [],
                    safe=False,
                )

            responsables = list(
                perfil.unidad_organizacional
                .obtener_usuarios(
                    incluir_self=False,
                )
            )

            if not responsables:
                return JsonResponse(
                    [],
                    safe=False,
                )

        responsables_ids = {
            usuario.pk
            for usuario in responsables
        }

        ejecuciones = (
            Ejecucion.objects
            .filter(
                responsable__in=responsables,
                ciclo__accion__plan__in=(
                    visible_plans
                ),
            )
            .select_related(
                "ciclo",
                "ciclo__accion",
                "ciclo__accion__plan",
                "responsable",
                "responsable__profile",
                "responsable__profile__unidad_organizacional",
            )
            .prefetch_related(
                "evidencia_registrada",
            )
            .order_by(
                "ciclo__fecha_fin",
                "responsable__first_name",
                "responsable__last_name",
                "pk",
            )
        )

        if fecha_inicio:
            ejecuciones = (
                ejecuciones.filter(
                    ciclo__fecha_fin__gte=(
                        fecha_inicio
                    )
                )
            )

        if fecha_fin:
            ejecuciones = (
                ejecuciones.filter(
                    ciclo__fecha_fin__lt=(
                        fecha_fin
                    )
                )
            )

        eventos = []

        eventos_existentes = set()

        hoy = timezone.localdate()

        for ejecucion in ejecuciones:
            actividad = strip_tags(
                ejecucion.accion.accion
                or ""
            ).strip()

            if not actividad:
                actividad = (
                    f"Actividad "
                    f"{ejecucion.accion_id}"
                )

            if (
                ejecucion.accion.formato_evidencia
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

            responsable = ejecucion.responsable.profile.nombre_calendario

            titulo = actividad

            if modo == "supervision":
                titulo = (
                    f"{responsable} — "
                    f"{actividad}"
                )

            unidad = ""

            if (
                ejecucion.responsable
                and ejecucion.responsable.profile
                .unidad_organizacional
            ):
                unidad = (
                    ejecucion.responsable
                    .profile
                    .unidad_organizacional
                    .clave
                )

            eventos_existentes.add(
                (
                    ejecucion.accion.pk,
                    ejecucion.ambito,
                    ejecucion.fecha_fin,
                )
            )

            eventos.append(
                {
                    "id": str(
                        ejecucion.pk
                    ),
                    "title": titulo,
                    "start": (
                        ejecucion.fecha_fin
                        .isoformat()
                    ),
                    "allDay": True,
                    "extendedProps": {
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
                        "folio": (
                            ejecucion.plan.folio
                            or ""
                        ),
                        "ciclo": (
                            ejecucion.ciclo.etiqueta
                        ),
                        "ambito": (
                            ejecucion
                            .get_ambito_display()
                        ),
                        "responsable": (
                            responsable
                        ),
                        "unidad": unidad,
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
                        "modo": modo,
                        "proyectada": False,
                    },
                }
            )

        if (
            fecha_inicio
            and fecha_fin
        ):
            actividades = (
                Accion.objects
                .filter(
                    plan__in=visible_plans,
                    periodicidad__in=[
                        PERIODICIDAD_SEMANAL,
                        PERIODICIDAD_QUINCENAL,
                        PERIODICIDAD_MENSUAL,
                        PERIODICIDAD_BIMESTRAL,
                        PERIODICIDAD_TRIMESTRAL,
                    ],
                )
                .select_related(
                    "plan",
                    "responsable",
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
                    or ["JL"]
                )

                descripcion = strip_tags(
                    actividad.accion
                    or ""
                ).strip()

                if not descripcion:
                    descripcion = (
                        f"Actividad "
                        f"{actividad.pk}"
                    )

                for ambito in ambitos:
                    responsable = (
                        actividad
                        .resolver_responsable_ejecucion(
                            ambito
                        )
                    )

                    if (
                        not responsable
                        or responsable.pk
                        not in responsables_ids
                    ):
                        continue

                    responsable_nombre = (
                        responsable.get_full_name()
                        or responsable.username
                    )

                    unidad = ""

                    if (
                        responsable.profile
                        .unidad_organizacional
                    ):
                        unidad = (
                            responsable.profile
                            .unidad_organizacional
                            .clave
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

                        estado = (
                            "programada"
                            if fecha > hoy
                            else "pendiente"
                        )

                        estado_display = (
                            "Programada"
                            if fecha > hoy
                            else "Pendiente"
                        )

                        titulo = descripcion

                        if (
                            modo
                            == "supervision"
                        ):
                            titulo = (
                                f"{responsable_nombre} — "
                                f"{descripcion}"
                            )

                        if (
                            actividad.formato_evidencia
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
                                    "planId": (
                                        actividad.plan.pk
                                    ),

                                    "plan": (
                                        actividad.plan.nombre
                                    ),

                                    "planUrl": reverse(
                                        "pas:detalle",
                                        args=[
                                            actividad.plan.pk
                                        ],
                                    ),

                                    "folio": (
                                        actividad.plan.folio
                                        or ""
                                    ),

                                    "ciclo": (
                                        "Proyección"
                                    ),

                                    "ambito": (
                                    dict(AMBITO).get(
                                            ambito,
                                            ambito,
                                        )
                                    ),

                                    "responsable": (
                                        responsable_nombre
                                    ),

                                    "unidad": unidad,

                                    "estado": estado,

                                    "estadoDisplay": (
                                        estado_display
                                    ),

                                    "evidencia": (
                                        evidencia
                                    ),

                                    "completada": False,

                                    "modo": modo,

                                    "proyectada": True,
                                },
                            }
                        )

        eventos.sort(
            key=lambda evento: (
                evento["start"],
                evento["title"],
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


class PlanSummaryView(DetailView):
    model = Plan
    template_name = "pas/partials/_plan_summary.html"

    def get_queryset(self):
        return Plan.objects.visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.object
        followups_prefetch = Prefetch(
            "seguimiento_set",
            queryset=Seguimiento.objects.order_by(
                "-fecha",
                "-created",
            ),
        )
        activities = list(plan.accion_set.prefetch_related(followups_prefetch))
        total = len(activities)
        closed = sum(1 for activity in activities if activity.get_estado == "Cerrada")
        progress = round((closed / total) * 100) if total else 0
        context.update(
            {
                "plan": plan,
                "total_activities": total,
                "closed_activities": closed,
                "open_activities": total - closed,
                "progress": progress,
                "all_closed": total > 0 and closed == total,
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )

        plan = self.object
        hoy = timezone.localdate()

        followups_prefetch = Prefetch(
            "seguimiento_set",
            queryset=Seguimiento.objects
            .select_related(
                "responsable"
            )
            .order_by(
                "-fecha",
                "-created",
            ),
        )

        executions_prefetch = Prefetch(
            "ejecuciones",
            queryset=Ejecucion.objects
            .select_related(
                "responsable",
            )
            .prefetch_related(
                "evidencia_registrada",
            )
            .order_by(
                "ambito",
            ),
        )

        cycles_prefetch = Prefetch(
            "ciclos",
            queryset=CicloActividad.objects
            .prefetch_related(
                executions_prefetch,
            )
            .order_by(
                "fecha_inicio",
                "numero",
            ),
        )

        activities_queryset = (
            plan.accion_set
            .select_related(
                "responsable"
            )
            .prefetch_related(
                followups_prefetch,
                cycles_prefetch,
            )
            .order_by(
                "fecha_fin",
                "id",
            )
        )

        def state_priority(estado):
            if estado == "Abierta Fuera de Tiempo":
                return 0

            if estado == "Cerrada":
                return 3

            if estado == "Abierta en Tiempo":
                return 2

            return 1

        def build_estado_badge(
            estado,
            closed_in_time,
        ):
            if estado == "Abierta Fuera de Tiempo":
                return {
                    "classes": (
                        "badge-error "
                        "text-error-content"
                    ),
                    "text": "Abierta",
                    "title": (
                        "Abierta fuera de tiempo"
                    ),
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
                    "title": (
                        "Abierta en tiempo"
                    ),
                }

            if estado == "Cerrada":
                if closed_in_time is False:
                    return {
                        "classes": (
                            "badge-success "
                            "badge-outline "
                            "text-success"
                        ),
                        "text": "Cerrada",
                        "title": (
                            "Cerrada fuera de tiempo"
                        ),
                    }

                return {
                    "classes": (
                        "badge-success "
                        "text-success-content"
                    ),
                    "text": "Cerrada",
                    "title": (
                        "Cerrada en tiempo"
                    ),
                }

            return {
                "classes": (
                    "badge-neutral "
                    "badge-outline"
                ),
                "text": (
                    estado or "Sin estado"
                ),
                "title": (
                    estado or "Sin estado"
                ),
            }

        def get_reference_cycle(cycles):
            if not cycles:
                return None

            current = next(
                (
                    cycle
                    for cycle in cycles
                    if (
                        cycle.fecha_inicio
                        <= hoy
                        <= cycle.fecha_fin
                    )
                ),
                None,
            )

            if current:
                return current

            future = next(
                (
                    cycle
                    for cycle in cycles
                    if cycle.fecha_inicio > hoy
                ),
                None,
            )

            if future:
                return future

            return cycles[-1]

        activities = []

        for activity in activities_queryset:
            estado = activity.get_estado
            followups = list(
                activity.seguimiento_set.all()
            )

            cycles = list(
                activity.ciclos.all()
            )

            reference_cycle = (
                get_reference_cycle(cycles)
            )

            execution_summary = []

            if reference_cycle:
                for execution in (
                    reference_cycle
                    .ejecuciones.all()
                ):
                    execution_summary.append(
                        {
                            "execution": execution,
                            "ambito": (
                                execution.ambito
                            ),
                            "ambito_display": (
                                execution
                                .get_ambito_display()
                            ),
                            "tiene_evidencia": (
                                execution
                                .tiene_evidencia
                            ),
                            "estado": (
                                execution
                                .estado_agenda
                            ),
                        }
                    )

            closure_followup = next(
                (
                    followup
                    for followup in followups
                    if followup.estado == CERRADA
                ),
                None,
            )

            closed_in_time = None

            if closure_followup:
                if activity.fecha_fin:
                    closed_in_time = (
                        closure_followup.fecha
                        <= activity.fecha_fin
                    )
                else:
                    closed_in_time = True

            activities.append(
                {
                    "activity": activity,
                    "estado": estado,
                    "estado_priority": (
                        state_priority(
                            estado
                        )
                    ),
                    "followup_count": len(
                        followups
                    ),
                    "latest_followup": (
                        followups[0]
                        if followups
                        else None
                    ),
                    "closed_in_time": (
                        closed_in_time
                    ),
                    "badge": (
                        build_estado_badge(
                            estado,
                            closed_in_time,
                        )
                    ),
                    "reference_cycle": (
                        reference_cycle
                    ),
                    "execution_summary": (
                        execution_summary
                    ),
                    "execution_total": len(
                        execution_summary
                    ),
                    "execution_with_evidence": sum(
                        1
                        for item
                        in execution_summary
                        if item[
                            "tiene_evidencia"
                        ]
                    ),
                }
            )

        activities.sort(
            key=lambda item: (
                item["estado_priority"],
                (
                    item["activity"].fecha_fin
                    or date.max
                ),
                item["activity"].pk,
            )
        )

        context.update(
            {
                "plan": plan,
                "activities": activities,
                "can_modify": (
                    plan.permite_modificaciones
                ),
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


class PlanUpdateView(PermissionRequiredMixin, PlanFormMixin, UpdateView):
    permission_required = "pas.change_plan"
    model = Plan
    form_class = PlanForm
    template_name = "pas/partials/_plan_form.html"

    def get_success_url(self):
        return reverse("pas:detalle", args=[self.object.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            header = hx_trigger_header("pas:refresh-summary", "pas:close-modal")
            return HttpResponse("", status=204, headers={"HX-Trigger": header})
        return response


class PlanClosureView(PermissionRequiredMixin, FormView):
    permission_required = "pas.change_plan"
    form_class = PlanClosureForm
    template_name = "pas/partials/_plan_closure_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.plan = get_object_or_404(Plan, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

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

    def get_initial(self):
        initial = super().get_initial()
        if self.plan.eliminacion:
            initial["resultado"] = "close"
            initial["comentarios"] = self.plan.txt_eliminacion
        elif self.plan.recurrencia:
            initial["resultado"] = "recurrence"
            initial["comentarios"] = self.plan.txt_recurrencia
        return initial

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request"):
            return self.render_to_response(self.get_context_data(form=form), status=422)
        return super().form_invalid(form)

    def form_valid(self, form):
        resultado = form.cleaned_data["resultado"]
        comentarios = form.cleaned_data.get("comentarios")

        if resultado == "close":
            self.plan.eliminacion = True
            self.plan.txt_eliminacion = comentarios
            self.plan.recurrencia = False
            self.plan.txt_recurrencia = ""
        else:
            self.plan.recurrencia = True
            self.plan.txt_recurrencia = comentarios
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

        if self.request.headers.get("HX-Request"):
            header = hx_trigger_header("pas:refresh-summary", "pas:close-modal")
            return HttpResponse("", status=204, headers={"HX-Trigger": header})

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pas:detalle", args=[self.plan.pk])


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

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request"):
            return self.render_to_response(self.get_context_data(form=form), status=422)
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


class ActivityCreateView(PermissionRequiredMixin, ActivityBaseView, CreateView):
    permission_required = "pas.add_accion"
    model = Accion

    def dispatch(self, request, *args, **kwargs):
        self.plan = get_object_or_404(Plan, pk=kwargs["pk"])
        if not self.plan.permite_modificaciones:
            return HttpResponse(
                "El plan se encuentra cerrado o con recurrencia registrada.",
                status=409,
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.plan = self.plan
        form.instance.user = self.request.user
        return super().form_valid(form)


class ActivityUpdateView(PermissionRequiredMixin, ActivityBaseView, UpdateView):
    permission_required = "pas.change_accion"
    model = Accion

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self.plan = obj.plan
        if not self.plan.permite_modificaciones:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "El plan se encuentra cerrado o con recurrencia registrada."
            )
        return obj


class ActivityDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "pas.delete_accion"
    model = Accion
    template_name = "pas/partials/_confirm_delete.html"

    def get_success_url(self):
        return reverse("pas:detalle", args=[self.object.plan.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "activity": self.object,
                "form_action": self.request.path,
                "modal_id": "pas-modal",
            }
        )
        return context

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        if obj.plan.eliminacion or obj.plan.recurrencia:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "El plan se encuentra cerrado o con recurrencia registrada."
            )

        return obj

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        response = super().delete(request, *args, **kwargs)
        if request.headers.get("HX-Request"):
            header = hx_trigger_header(
                "pas:refresh-activities", "pas:refresh-summary", "pas:close-modal"
            )
            return HttpResponse("", status=204, headers={"HX-Trigger": header})
        return response


class FollowUpBaseView(CreateView):
    model = Seguimiento
    form_class = SeguimientoForm
    template_name = "pas/partials/_followup_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.activity = get_object_or_404(Accion, pk=kwargs["pk"])

        if self.activity.plan.eliminacion or self.activity.plan.recurrencia:
            return HttpResponse(
                "El plan se encuentra cerrado o con recurrencia registrada.",
                status=409,
            )

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("pas:detalle", args=[self.activity.plan.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_action": self.request.path,
                "activity": self.activity,
                "modal_id": "pas-modal",
            }
        )
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("fecha", timezone.now().date())
        return initial

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request"):
            return self.render_to_response(self.get_context_data(form=form), status=422)
        return super().form_invalid(form)

    def form_valid(self, form):
        form.instance.accion = self.activity
        form.instance.user = self.request.user
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            header = hx_trigger_header(
                "pas:refresh-activities", "pas:refresh-summary", "pas:close-modal"
            )
            return HttpResponse("", status=204, headers={"HX-Trigger": header})
        return response


class FollowUpCreateView(PermissionRequiredMixin, FollowUpBaseView):
    permission_required = "pas.add_seguimiento"

    pass


class FollowUpListView(DetailView):
    model = Accion
    template_name = "pas/partials/_followup_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        followups = self.object.seguimiento_set.select_related("responsable").order_by(
            "-fecha", "-created"
        )
        context.update(
            {
                "activity": self.object,
                "followups": followups,
            }
        )
        return context


class EvidenceBaseView(CreateView):
    model = Evidencia
    form_class = EvidenciaForm
    template_name = "pas/partials/_evidence_form.html"

    def dispatch(self, request, *args, **kwargs):
        visible_plans = Plan.objects.visible_to(request.user)

        self.activity = get_object_or_404(
            Accion.objects.select_related("plan").filter(
                plan__in=visible_plans
            ),
            pk=kwargs["pk"],
        )

        if not self.activity.plan.permite_modificaciones:
            return HttpResponse(
                "El plan se encuentra cerrado o con recurrencia registrada.",
                status=409,
            )

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "pas:detalle",
            args=[self.activity.plan.pk],
        )

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("fecha", timezone.localdate())
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "activity": self.activity,
                "form_action": self.request.path,
                "modal_id": "pas-modal",
            }
        )
        return context

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request"):
            return self.render_to_response(
                self.get_context_data(form=form),
                status=422,
            )

        return super().form_invalid(form)

    def form_valid(self, form):
        form.instance.accion = self.activity
        form.instance.user = self.request.user

        response = super().form_valid(form)

        if self.request.headers.get("HX-Request"):
            header = hx_trigger_header(
                "pas:refresh-activities",
                "pas:close-modal",
            )
            return HttpResponse(
                "",
                status=204,
                headers={"HX-Trigger": header},
            )

        return response


class EvidenceCreateView(
    PermissionRequiredMixin,
    EvidenceBaseView,
):
    permission_required = "pas.add_evidencia"


class EvidenceListView(DetailView):
    model = Accion
    template_name = "pas/partials/_evidence_list.html"

    def get_queryset(self):
        visible_plans = Plan.objects.visible_to(
            self.request.user
        )

        return (
            Accion.objects
            .filter(plan__in=visible_plans)
            .select_related("plan")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evidences = (
            self.object.evidencias
            .select_related("user")
            .order_by("-fecha", "-created")
        )

        context.update(
            {
                "activity": self.object,
                "evidences": evidences,
            }
        )

        return context


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
        visible_plans = (
            Plan.objects.visible_to(
                request.user
            )
        )

        self.execution = get_object_or_404(
            Ejecucion.objects
            .select_related(
                "ciclo",
                "ciclo__accion",
                "ciclo__accion__plan",
                "responsable",
            )
            .filter(
                ciclo__accion__plan__in=(
                    visible_plans
                ),
            ),
            pk=kwargs["pk"],
        )

        if (
            self.execution.accion.formato_evidencia
            == FORMATO_SIN_EVIDENCIA
        ):
            return HttpResponse(
                (
                    "Esta actividad no requiere "
                    "evidencia documental."
                ),
                status=409,
            )

        if (
            not self.execution.plan
            .permite_modificaciones
        ):
            return HttpResponse(
                (
                    "El plan se encuentra cerrado "
                    "o con recurrencia registrada."
                ),
                status=409,
            )

        if Evidencia.objects.filter(
            ejecucion=self.execution
        ).exists():
            return HttpResponse(
                (
                    "Esta ejecución ya tiene una "
                    "evidencia registrada."
                ),
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

        if self.request.headers.get(
            "HX-Request"
        ):
            header = hx_trigger_header(
                "pas:refresh-activities",
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
                "responsable",
            )
            .filter(
                ciclo__accion__plan__in=(
                    visible_plans
                )
            ),
            pk=kwargs["pk"],
        )

        puede_actualizar = (
            execution.responsable_id
            == request.user.id
            or request.user.has_perm(
                "pas.change_ejecucion"
            )
        )

        if not puede_actualizar:
            return HttpResponse(
                (
                    "No tienes permiso para "
                    "actualizar esta ejecución."
                ),
                status=403,
            )

        if not execution.plan.permite_modificaciones:
            return HttpResponse(
                (
                    "El plan se encuentra cerrado "
                    "o con recurrencia registrada."
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
            return HttpResponse(
                "",
                status=204,
                headers={
                    "HX-Refresh": "true",
                },
            )

        return HttpResponse(
            status=204
        )
