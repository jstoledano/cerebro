import json

from datetime import date

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Prefetch
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    DeleteView,
)
from .forms import PlanForm, AccionForm, SeguimientoForm, PlanClosureForm, EvidenciaForm
from .models import Plan, Accion, Seguimiento, Evidencia, CERRADA


def hx_trigger_header(*events):
    if not events:
        return ""
    payload = {event: "" for event in events}
    return json.dumps(payload)


class PASIndex(ListView):
    model = Plan
    template_name = "pas/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        followups_prefetch = Prefetch(
            "seguimiento_set",
            queryset=Seguimiento.objects.select_related("responsable").order_by(
                "-fecha",
                "-created",
            ),
        )

        plan_actions_prefetch = Prefetch(
            "accion_set",
            queryset=(
                Accion.objects.select_related("responsable").prefetch_related(
                    followups_prefetch
                )
            ),
            to_attr="pas_actions",
        )

        plan_list = (
            Plan.objects.visible_to(self.request.user)
            .prefetch_related(plan_actions_prefetch)
            .order_by("-fecha_llenado")
        )

        def state_priority(estado):
            if estado == "Abierta Fuera de Tiempo":
                return 0
            if estado == "Cerrada":
                return 3
            if estado == "Abierta en Tiempo":
                return 2
            return 1

        action_items = []
        action_qs = Accion.objects.select_related(
            "plan", "responsable"
        ).prefetch_related(followups_prefetch)

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

        action_items.sort(key=lambda item: (item[0], item[1], item[2]))
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
        return Plan.objects.visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.object

        followups_prefetch = Prefetch(
            "seguimiento_set",
            queryset=Seguimiento.objects.select_related(
                "responsable"
            ).order_by(
                "-fecha",
                "-created",
            ),
        )

        activities_queryset = (
            plan.accion_set
            .select_related("responsable")
            .annotate(
                evidence_count=Count("evidencias")
            )
            .prefetch_related(
                followups_prefetch,
            )
            .order_by("fecha_fin", "id")
        )

        def state_priority(estado):
            if estado == "Abierta Fuera de Tiempo":
                return 0
            if estado == "Cerrada":
                return 3
            if estado == "Abierta en Tiempo":
                return 2
            return 1

        def build_estado_badge(estado, closed_in_time):
            if estado == "Abierta Fuera de Tiempo":
                return {
                    "classes": "badge-error text-error-content",
                    "text": "Abierta",
                    "title": "Abierta fuera de tiempo",
                }

            if estado == "Abierta en Tiempo":
                return {
                    "classes": (
                        "badge-outline border border-warning "
                        "text-base-content bg-transparent"
                    ),
                    "text": "Abierta",
                    "title": "Abierta en tiempo",
                }

            if estado == "Cerrada":
                if closed_in_time is False:
                    return {
                        "classes": (
                            "badge-success badge-outline text-success"
                        ),
                        "text": "Cerrada",
                        "title": "Cerrada fuera de tiempo",
                    }

                return {
                    "classes": "badge-success text-success-content",
                    "text": "Cerrada",
                    "title": "Cerrada en tiempo",
                }

            return {
                "classes": "badge-neutral badge-outline",
                "text": estado or "Sin estado",
                "title": estado or "Sin estado",
            }

        activities = []

        for activity in activities_queryset:
            estado = activity.get_estado

            followups = list(
                activity.seguimiento_set.all()
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
                    "estado_priority": state_priority(
                        estado
                    ),
                    "followup_count": len(followups),
                    "evidence_count": (
                        activity.evidence_count
                    ),
                    "latest_followup": (
                        followups[0]
                        if followups
                        else None
                    ),
                    "closed_in_time": closed_in_time,
                    "badge": build_estado_badge(
                        estado,
                        closed_in_time,
                    ),
                }
            )

        activities.sort(
            key=lambda item: (
                item["estado_priority"],
                item["activity"].fecha_fin or date.max,
                item["activity"].pk,
            )
        )

        can_modify = plan.permite_modificaciones

        context.update(
            {
                "plan": plan,
                "activities": activities,
                "can_modify": can_modify,
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
        if self.request.headers.get("HX-Request"):
            header = hx_trigger_header(
                "pas:refresh-activities", "pas:refresh-summary", "pas:close-modal"
            )
            return HttpResponse("", status=204, headers={"HX-Trigger": header})
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


class EvidenceDownloadView(DetailView):
    model = Evidencia

    def get_queryset(self):
        visible_plans = Plan.objects.visible_to(self.request.user)

        return (
            Evidencia.objects
            .filter(accion__plan__in=visible_plans)
            .select_related(
                "accion",
                "accion__plan",
            )
        )

    def get(self, request, *args, **kwargs):
        evidence = self.get_object()

        if not evidence.archivo:
            raise Http404("La evidencia no tiene archivo.")

        return FileResponse(
            evidence.archivo.open("rb"),
            as_attachment=False,
            filename=evidence.archivo.name.rsplit("/", 1)[-1],
        )
