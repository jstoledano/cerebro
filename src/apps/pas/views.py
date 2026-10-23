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
    PERIODICIDAD_ANUAL,
    PRIORIDAD_URGENTE,
    PRIORIDAD_CRITICA,
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

        # ==================================================
        # Generación de ejecuciones recurrentes abiertas
        # ==================================================

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

        # ==================================================
        # Personas incluidas en la agenda
        # ==================================================

        perfil = getattr(
            self.request.user,
            "profile",
            None,
        )

        if perfil:
            usuarios_agenda = list(
                perfil.obtener_usuarios_agenda()
            )
        else:
            usuarios_agenda = [
                self.request.user
            ]

        usuarios_agenda_ids = {
            usuario.pk
            for usuario in usuarios_agenda
        }

        es_supervisor_agenda = (
            perfil.es_supervisor_agenda
            if perfil
            else False
        )

        claves_normativas = obtener_claves_normativas_agenda(perfil)

        # ==================================================
        # Ejecuciones visibles en la agenda consolidada
        # ==================================================

        ejecuciones = list(
            Ejecucion.objects.filter(
                Q(responsable__in=(usuarios_agenda))
                | Q(ciclo__accion__puesto_responsable__in=(claves_normativas)),
                ciclo__accion__plan__in=(visible_plans),
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
            .distinct()
            .order_by(
                "ciclo__fecha_fin",
                "ciclo__fecha_inicio",
                "responsable__first_name",
                "responsable__last_name",
                "ciclo__accion_id",
            )
        )

        # ==================================================
        # Clasificación por nivel de atención
        # ==================================================

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

            # Marca útil para el template.
            ejecucion.es_mia = (
                ejecucion.responsable_id
                == self.request.user.id
            )

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

            # ----------------------------------------------
            # 1. URGENTE
            # ----------------------------------------------

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

            # ----------------------------------------------
            # 2. REQUIERE ATENCIÓN
            # ----------------------------------------------

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

            # ----------------------------------------------
            # 3. VIGILAR
            # ----------------------------------------------

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

        # ==================================================
        # Contexto
        # ==================================================

        context.update(
            {
                "hoy": hoy,
                "inicio_semana": (inicio_semana),
                "fin_semana": (fin_semana),
                # ------------------------------------------
                # Alcance de agenda
                # ------------------------------------------
                "usuarios_agenda": (usuarios_agenda),
                "usuarios_agenda_ids": (usuarios_agenda_ids),
                "es_supervisor_agenda": (es_supervisor_agenda),
                "total_usuarios_agenda": len(usuarios_agenda),
                "claves_normativas": (claves_normativas),
                # ------------------------------------------
                # Radar
                # ------------------------------------------
                "urgentes": (urgente),
                "requieren_atencion": (atencion),
                "vigilar": (vigilar),
                "terminadas": (terminadas),
                # ------------------------------------------
                # Subcategorías
                # ------------------------------------------
                "vencidas": (vencidas),
                "vencen_hoy": (vencen_hoy),
                "vencen_semana": (vencen_semana),
                "prioridad_alta": (prioridad_alta),
                "inician_hoy": (inician_hoy),
                "inician_semana": (inician_semana),
                # ------------------------------------------
                # Totales
                # ------------------------------------------
                "total_urgentes": len(urgente),
                "total_requieren_atencion": len(atencion),
                "total_vigilar": len(vigilar),
                "total_terminadas": len(terminadas),
                "total_vencidas": len(vencidas),
                "total_vencen_hoy": len(vencen_hoy),
                "total_vencen_semana": len(vencen_semana),
                "total_prioridad_alta": len(prioridad_alta),
                "total_inician_hoy": len(inician_hoy),
                "total_inician_semana": len(inician_semana),
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

        # ==================================================
        # Personas incluidas en la agenda
        # ==================================================

        perfil = getattr(
            request.user,
            "profile",
            None,
        )

        if perfil:
            responsables = list(perfil.obtener_usuarios_agenda())

            es_supervisor_agenda = perfil.es_supervisor_agenda

            claves_normativas = obtener_claves_normativas_agenda(perfil)

        else:
            responsables = [request.user]

            es_supervisor_agenda = False

            claves_normativas = set()

        responsables_ids = {
            usuario.pk
            for usuario in responsables
        }

        # ==================================================
        # Nombre corto para calendario
        # ==================================================

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

        # ==================================================
        # Ejecuciones materializadas
        # ==================================================

        ejecuciones = (
            Ejecucion.objects.filter(
                Q(responsable__in=(responsables))
                | Q(ciclo__accion__puesto_responsable__in=(claves_normativas)),
                ciclo__accion__plan__in=(visible_plans),
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
            .distinct()
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

            responsable_nombre = (
                nombre_calendario(
                    ejecucion.responsable
                )
            )

            es_mia = (
                ejecucion.responsable_id
                == request.user.id
            )

            # En una agenda jerárquica siempre identificamos
            # quién ejecuta la tarea.
            if es_supervisor_agenda:
                if es_mia:
                    titulo = (
                        f"YO — {actividad}"
                    )
                else:
                    titulo = (
                        f"{responsable_nombre} — "
                        f"{actividad}"
                    )
            else:
                titulo = actividad

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
                            responsable_nombre
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

                        "esMia": es_mia,

                        "proyectada": False,
                    },
                }
            )

        # ==================================================
        # Proyecciones de recurrencias
        # ==================================================

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

                    es_operativamente_visible = (
                        responsable and responsable.pk in responsables_ids
                    )

                    es_normativamente_visible = (
                        actividad.puesto_responsable in claves_normativas
                    )

                    if not es_operativamente_visible and not es_normativamente_visible:
                        continue

                    responsable_nombre = (
                        nombre_calendario(
                            responsable
                        )
                    )

                    es_mia = (
                        responsable is not None and responsable.pk == request.user.id
                    )

                    unidad = ""

                    perfil_responsable = getattr(
                        responsable,
                        "profile",
                        None,
                    )

                    if (
                        perfil_responsable
                        and perfil_responsable
                        .unidad_organizacional
                    ):
                        unidad = (
                            perfil_responsable
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

                        if fecha > hoy:
                            estado = (
                                "programada"
                            )

                            estado_display = (
                                "Programada"
                            )

                        else:
                            estado = (
                                "pendiente"
                            )

                            estado_display = (
                                "Pendiente"
                            )

                        if es_supervisor_agenda:
                            if es_mia:
                                titulo = (
                                    f"YO — "
                                    f"{descripcion}"
                                )
                            else:
                                titulo = (
                                    f"{responsable_nombre}"
                                    f" — "
                                    f"{descripcion}"
                                )
                        else:
                            titulo = (
                                descripcion
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
                                        dict(
                                            AMBITO
                                        ).get(
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

                                    "esMia": es_mia,

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
            .order_by(
                "id"
            )
        )

        tiene_avance = bool(
            plan.fecha_termino
        )

        total_ejecuciones = 0
        ejecuciones_terminadas = 0
        ejecuciones_pendientes = 0
        progress = None

        if tiene_avance:

            # ----------------------------------------------
            # Materializar todo el universo finito
            # ----------------------------------------------

            for activity in activities:

                if (
                    activity.periodicidad
                    == PERIODICIDAD_MANUAL
                ):
                    # Las actividades manuales ya deben tener
                    # sus ciclos definidos explícitamente.
                    continue

                activity.generar_ejecuciones()

            # ----------------------------------------------
            # Ejecuciones que pertenecen al horizonte
            # temporal del plan
            # ----------------------------------------------

            executions = (
                Ejecucion.objects
                .filter(
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
        # Cierre administrativo del plan
        # --------------------------------------------------
        #
        # Conservamos por ahora la lógica existente para
        # determinar si todas las actividades están cerradas.
        # Esto es distinto al porcentaje de ejecuciones.
        # --------------------------------------------------

        followups_prefetch = Prefetch(
            "seguimiento_set",
            queryset=(
                Seguimiento.objects
                .order_by(
                    "-fecha",
                    "-created",
                )
            ),
        )

        activities_with_followups = list(
            plan.accion_set
            .prefetch_related(
                followups_prefetch
            )
        )

        total_activities = len(
            activities_with_followups
        )

        closed_activities = sum(
            1
            for activity
            in activities_with_followups
            if activity.get_estado == "Cerrada"
        )

        open_activities = (
            total_activities
            - closed_activities
        )

        all_closed = (
            total_activities > 0
            and closed_activities
            == total_activities
        )

        context.update(
            {
                "plan": plan,

                # Definiciones de actividad
                "total_activities": (
                    total_activities
                ),
                "closed_activities": (
                    closed_activities
                ),
                "open_activities": (
                    open_activities
                ),
                "all_closed": (
                    all_closed
                ),

                # Avance real
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
                "progress": (
                    progress
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
        context = super().get_context_data(
            **kwargs
        )

        plan = self.object
        hoy = timezone.localdate()

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

        executions_prefetch = Prefetch(
            "ejecuciones",
            queryset=(
                Ejecucion.objects
                .select_related(
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
                CicloActividad.objects
                .prefetch_related(
                    executions_prefetch,
                )
                .order_by(
                    "fecha_inicio",
                    "numero",
                )
            ),
        )

        activities_queryset = (
            plan.accion_set
            .select_related(
                "responsable",
                "responsable__profile",
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

        def state_priority(
            estado,
        ):
            if (
                estado
                == "Abierta Fuera de Tiempo"
            ):
                return 0

            if estado == "Cerrada":
                return 3

            if (
                estado
                == "Abierta en Tiempo"
            ):
                return 2

            return 1

        def build_estado_badge(
            estado,
            closed_in_time,
        ):
            if (
                estado
                == "Abierta Fuera de Tiempo"
            ):
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

            if (
                estado
                == "Abierta en Tiempo"
            ):
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
                    estado
                    or "Sin estado"
                ),
                "title": (
                    estado
                    or "Sin estado"
                ),
            }

        def ciclo_pendiente(
            cycles,
        ):
            """
            Devuelve el primer ciclo que todavía
            tenga al menos una ejecución pendiente.

            Puede ser vencido, actual o futuro.
            """
            for cycle in cycles:
                executions = list(
                    cycle.ejecuciones.all()
                )

                if not executions:
                    continue

                if any(
                    not execution.completada
                    for execution
                    in executions
                ):
                    return cycle

            return None

        def ciclo_referencia(
            cycles,
        ):
            """
            Ciclo usado para el resumen de evidencias.

            Primero usa la próxima obligación pendiente.
            Si todo está terminado, conserva el último
            ciclo como referencia histórica.
            """
            pending = ciclo_pendiente(
                cycles
            )

            if pending:
                return pending

            if cycles:
                return cycles[-1]

            return None

        def descripcion_corta(
            activity,
        ):
            texto = strip_tags(
                activity.accion or ""
            )

            texto = " ".join(
                texto.split()
            )

            limite = 125

            if len(texto) <= limite:
                return texto

            return (
                texto[:limite]
                .rstrip()
                + "…"
            )

        def nombre_compacto(
            usuario,
        ):
            if not usuario:
                return "—"

            try:
                profile = usuario.profile

                if (
                    profile
                    and profile.nombre_calendario
                ):
                    return (
                        profile.nombre_calendario
                    )

            except Exception:
                pass

            nombre = (
                usuario.get_full_name()
                or usuario.username
            )

            return nombre[:10]

        def responsables_ciclo(
            cycle,
        ):
            if not cycle:
                return []

            nombres = []

            for execution in (
                cycle.ejecuciones.all()
            ):
                nombre = nombre_compacto(
                    execution.responsable
                )

                if (
                    nombre != "—"
                    and nombre not in nombres
                ):
                    nombres.append(
                        nombre
                    )

            return nombres

        activities = []

        for activity in activities_queryset:
            estado = activity.get_estado

            followups = list(
                activity.seguimiento_set.all()
            )

            cycles = list(
                activity.ciclos.all()
            )

            pending_cycle = (
                ciclo_pendiente(
                    cycles
                )
            )

            reference_cycle = (
                ciclo_referencia(
                    cycles
                )
            )

            execution_summary = []

            if reference_cycle:
                for execution in (
                    reference_cycle
                    .ejecuciones.all()
                ):
                    execution_summary.append(
                        {
                            "execution": (
                                execution
                            ),
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
                    for followup
                    in followups
                    if (
                        followup.estado
                        == CERRADA
                    )
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

            nombres_responsables = (
                responsables_ciclo(
                    pending_cycle
                    or reference_cycle
                )
            )

            if nombres_responsables:
                responsable_compacto = (
                    ", ".join(
                        nombres_responsables
                    )
                )

            elif activity.responsable_id:
                responsable_compacto = (
                    nombre_compacto(
                        activity.responsable
                    )
                )

            elif activity.puesto_responsable:
                responsable_compacto = (
                    activity
                    .get_puesto_responsable_display()
                )

            else:
                responsable_compacto = "—"

            activities.append(
                {
                    "activity": activity,

                    "descripcion_corta": (
                        descripcion_corta(
                            activity
                        )
                    ),

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

                    "proxima_accion": (
                        pending_cycle
                    ),

                    "responsable_compacto": (
                        responsable_compacto
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
                    item[
                        "proxima_accion"
                    ].fecha_fin
                    if item[
                        "proxima_accion"
                    ]
                    else date.max
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
