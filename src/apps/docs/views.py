"""
Aquí se controlan las vistas de la aplicación docs.

Incluye las siguientes vistas:
- Reportes
- IndexLMD (Lista Maestra de Documentos)
- IndexList, la portada
- DocDetail, el detalle de un documento
- DocAdd, para agregar un documento
- RevisionAdd, para agregar una revisión de un documento
- ProcesoList, la lista de procesos
- ProcesoAdd, para agregar un proceso
- TipoAdd, para agregar un tipo de documento
- Buscador, el buscador de documentos
"""

from datetime import datetime
from django.forms.models import BaseModelForm
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from watson import search as watson
from django.urls import reverse_lazy
from pathlib import Path
from django.db.models import Q, Prefetch
from django.views.generic import ListView, TemplateView, DetailView, FormView
from django.views.generic.edit import CreateView, UpdateView
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.contrib import messages
import os
import logging
from apps.docs.models import Documento, Proceso, Tipo, Revision, Reporte, Notificacion
from apps.profiles.models import Profile
from apps.docs.forms import (
    DocForm,
    ProcesoForm,
    ReporteForm,
    TipoForm,
    VersionForm,
    PanicResolveForm,
)


class HTMXDocumentListMixin:
    """Proporciona soporte para listas dinamicas usando htmx."""

    partial_template = "docs/partials/_doc_list.html"
    list_title = ""
    list_description = ""

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return [self.partial_template]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("list_title", self.list_title)
        context.setdefault("list_description", self.list_description)
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        revision_prefetch = Prefetch(
            "revision_set", queryset=Revision.objects.order_by("-revision")
        )
        return qs.select_related("tipo", "proceso").prefetch_related(revision_prefetch)


class Reportes(ListView):
    """
    Clase Reportes.

    Crea una vista tipo ListView que muestra los documentos en el
    grupo 'reportes'.
    """

    model = Documento
    context_object_name = "docs"

    def get_queryset(self):
        """La consulta que devuelve los documentos con slug 'RPT'."""
        return Documento.objects.filter(tipo__slug="RPT").order_by("id")

    def __str__(self):
        return self.__class__.__name__


class IndexLMD(HTMXDocumentListMixin, ListView):
    """
    Índice de la Lista Maestra de Documentos.

    Genera una ListView con los documentos en el proceso LMD.
    Cambiará en agosto de 2023 a una propiedad del documento.
    """

    model = Documento
    context_object_name = "docs"
    template_name = "docs/index.html"
    list_title = "Lista Maestra de Documentos"

    def get_queryset(self):
        return (
            Documento.objects.filter(lmd=True, activo=True)
            .select_related("proceso", "tipo")
            .prefetch_related("revision_set")
            .order_by("proceso", "nombre")
        )

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return [self.partial_template]
        return [self.template_name]

    def get_stats(self):
        base_qs = Documento.objects.filter(activo=True)
        return {
            "total": base_qs.count(),
            "lmd": base_qs.filter(lmd=True).count(),
            "procesos": base_qs.values("proceso").distinct().count(),
            "tipos": base_qs.values("tipo").distinct().count(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "stats": self.get_stats(),
                "processes": Proceso.objects.order_by("proceso"),
                "types": Tipo.objects.order_by("tipo"),
                "activeLMD": True,
            }
        )
        return context


class IndexLDP(HTMXDocumentListMixin, ListView):
    """Lista de documentos por proceso."""

    model = Documento
    template_name = "docs/list.html"
    context_object_name = "docs"
    list_title = "Documentos por proceso"
    list_description = "Documentos agrupados por cada proceso del SGC."

    def get_queryset(self):
        return (
            Documento.objects.filter(lmd=False, activo=True)
            .select_related("proceso", "tipo")
            .prefetch_related("revision_set")
            .order_by("proceso", "tipo")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activeLDP"] = True
        return context


class IndexLDT(HTMXDocumentListMixin, ListView):
    """Lista de documentos por tipo."""

    model = Documento
    template_name = "docs/list.html"
    context_object_name = "docs"
    list_title = "Documentos por tipo"
    list_description = "Filtra los documentos según su tipología."

    def get_queryset(self):
        return (
            Documento.objects.filter(lmd=False, activo=True)
            .select_related("proceso", "tipo")
            .prefetch_related("revision_set")
            .order_by("tipo", "proceso", "id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activeLDT"] = True
        return context


class IndexLDR(HTMXDocumentListMixin, ListView):
    """Lista de resultados del SGC."""

    model = Documento
    template_name = "docs/list.html"
    context_object_name = "docs"
    list_title = "Documentos con resultados"
    list_description = "Reportes y documentos con indicadores y resultados del SGC."

    def get_queryset(self):
        return (
            Documento.objects.filter(resultados=True, activo=True)
            .select_related("proceso", "tipo")
            .prefetch_related("revision_set")
            .order_by("proceso", "id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activeLDR"] = True
        return context


class IndexList(ListView):
    """
    Vista que genera la portada de la app docs.

    Se agrega al contexto el queryset `docs`.
    """

    model = Documento
    template_name = "docs/portada.html"
    context_object_name = "docs"

    def get_context_data(self, **kwargs):
        """Agregamos la variable panicButton al contexto de la vista."""
        context = super().get_context_data(**kwargs)
        context["panicButton"] = True
        return context

    def get_queryset(self):
        """Consulta para la portada. Todos los documentos."""
        return Documento.objects.filter(Q(activo=True)).order_by("proceso", "nombre")


class DocDetail(DetailView):
    """
    Es la vista para el detalle de documentos.

    Agrega al contexto `version` para el completado de la
    nueva revisión.
    """

    model = Documento
    context_object_name = "doc"
    template_name = "docs/documento_detail.html"

    def get_context_data(self, **kwargs):
        """Agrega la variable `version` al contexto de la vista."""
        context = super().get_context_data(**kwargs)
        # Buscamos los reportes que existan en el documento actual
        # y los agregamos al contexto
        context["reportes"] = Reporte.objects.filter(documento=self.kwargs["pk"])
        current_revision = self.object.revision_set.order_by("-revision").first()
        context["current_revision"] = current_revision
        if current_revision and current_revision.archivo:
            file_url = current_revision.archivo.url
            context["current_file_url"] = file_url
            context["current_file_abs_url"] = self.request.build_absolute_uri(file_url)
            context["current_file_ext"] = (
                Path(current_revision.archivo.name).suffix.lower().lstrip(".")
            )
            context["preview_image_exts"] = ["jpg", "jpeg", "png", "gif", "webp", "bmp"]
            context["preview_office_exts"] = [
                "doc",
                "docx",
                "xls",
                "xlsx",
                "ppt",
                "pptx",
            ]
        context["history"] = self.object.revision_set.order_by("-revision")[1:]
        next_revision = 0
        if current_revision:
            next_revision = current_revision.revision + 1
        context["revision_form"] = VersionForm(
            initial={
                "revision": next_revision,
                "f_actualizacion": datetime.today().date(),
            }
        )
        context["rev_add_url"] = reverse_lazy("docs:rev_add", args=(self.object.id,))
        return context


class SetupDoc(TemplateView):
    """
    Crea un nuevo documento.

    Esta clase crea un nuevo documento, establece su tipo y el proceso al que
    pertenece y agrega la primera versión.
    """

    template_name = "docs/setup.html"

    def get_context_data(self, **kwargs):
        """
        Agrega las siguientes variables al contexto.

        - `process_form`, es el formulario para crear un nuevo proceso.
        - `process`, el proceso al que pertenece el documento.
        - `types_form`: el formulario para agregar un nuevo tipo.
        - `type`: El tipo de documento.
        """
        context = super().get_context_data(**kwargs)
        process = Proceso.objects.all()
        types = Tipo.objects.all()
        context.update(
            {
                "process_form": ProcesoForm,
                "process": process,
                "types_form": TipoForm,
                "types": types,
            }
        )
        return context


class DocAdd(LoginRequiredMixin, CreateView):
    """Formulario para agregar un documento."""

    model = Documento
    form_class = DocForm
    template_name = "docs/documento_form.html"

    def get_context_data(self, **kwargs):
        """Agrega formularios de catálogo para usarlos en modales."""
        context = super().get_context_data(**kwargs)
        context.setdefault("process_form", ProcesoForm())
        context.setdefault("type_form", TipoForm())
        context["process_add_url"] = reverse_lazy("docs:process_add")
        context["type_add_url"] = reverse_lazy("docs:tipo_add")
        context["return_url"] = reverse_lazy("docs:add")
        return context

    def form_valid(self, form):
        """Validación del formulario."""
        document = form.save(commit=False)
        document.autor = self.request.user
        document.slug = slugify(document.nombre)
        document.save()
        form.save_m2m()
        messages.success(self.request, "El documento se registró correctamente.")
        self.object = document
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        """Redirección en caso de éxito."""
        return reverse_lazy("docs:detalle", args=(self.object.id,))


def envio_de_correo(request, destinatarios, asunto, documento, revision, autor):
    """
    Envía notificaciones por correo electrónico a una lista de destinatarios utilizando SMTP.
    """
    from_email = os.getenv("SMTP_USER", "cerebro@cmi.lat")
    for destinatario_profile in destinatarios:
        nombre_usuario = destinatario_profile.user.get_full_name()
        if not nombre_usuario:
            nombre_usuario = (
                destinatario_profile.user.username
                or destinatario_profile.user.email.split("@")[0]
            )

        mensaje_html = render_to_string(
            "docs/notificacion_urgente.html",
            {
                "documento": documento,
                "revision": revision,
                "autor": autor,
                "nombre_usuario": nombre_usuario,
                "site_url": settings.SITE_URL,
            },
        )
        try:
            send_mail(
                asunto,
                "",  # Mensaje de texto plano vacío
                f"SGC Tlaxcala <{from_email}>",
                [destinatario_profile.user.email],
                html_message=mensaje_html,
                fail_silently=False,
            )
        except Exception as e:
            messages.error(
                request,
                f"Error al enviar notificación a {destinatario_profile.user.email}: {e}",
            )


def send_message(request, destinatarios, asunto, documento, revision, autor):
    """
    Envía notificaciones por correo electrónico a una lista de destinatarios utilizando SMTP.
    """
    logger = logging.getLogger(__name__)
    from_email = os.getenv("SMTP_USER", "cerebro@cmi.lat")

    for destinatario_profile in destinatarios:
        nombre_usuario = destinatario_profile.user.get_full_name()
        if not nombre_usuario:
            nombre_usuario = (
                destinatario_profile.user.username
                or destinatario_profile.user.email.split("@")[0]
            )

        mensaje_html = render_to_string(
            "docs/notificacion_urgente.html",
            {
                "documento": documento,
                "revision": revision,
                "autor": autor,
                "nombre_usuario": nombre_usuario,
                "site_url": settings.SITE_URL,
            },
        )

        try:
            send_mail(
                asunto,
                "",
                f"SGC Tlaxcala <{from_email}>",
                [destinatario_profile.user.email],
                html_message=mensaje_html,
                fail_silently=False,
            )
        except Exception as e:
            logger.error(
                f"Error al enviar notificación a {destinatario_profile.user.email}: {e}"
            )
            messages.error(
                request,
                f"Error al enviar notificación a {destinatario_profile.user.email}: {e}",
            )

    logger.info(
        f"Notificación para '{documento.nombre}': Enviada a {destinatarios.count()} destinatarios."
    )


class RevisionAdd(LoginRequiredMixin, CreateView):
    """Formulario para crear una nueva revisión de un documento."""

    model = Revision
    form_class = VersionForm

    def dispatch(self, request, *args, **kwargs):
        """Crea un nuevo documento en el formulario."""
        self.doc = Documento.objects.get(pk=kwargs["pk"])
        return super(RevisionAdd, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(RevisionAdd, self).get_initial()
        try:
            revision = self.doc.revision_set.order_by("-revision")[0].revision + 1
        except IndexError:
            revision = 0
        fecha = datetime.today()
        initial["revision"] = revision
        initial["f_actualizacion"] = fecha
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"doc": self.doc})
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.documento = self.doc
        self.object.autor = self.request.user

        self.object.save()

        if self.object.notificacion_urgente:
            destinatarios = Profile.objects.filter(
                recibe_notificaciones=True, user__email__isnull=False
            )
            asunto = f"Notificación Urgente: Nueva Revisión de {self.doc.nombre}"

            if destinatarios.exists():
                send_message(
                    self.request,
                    destinatarios,
                    asunto,
                    self.doc,
                    self.object,
                    self.request.user,
                )

                # Render the message once for the notification record, using a generic user name
                mensaje_html_para_notificacion = render_to_string(
                    "docs/notificacion_urgente_content.html",
                    {
                        "documento": self.doc,
                        "revision": self.object,
                        "autor": self.request.user,
                        "nombre_usuario": "Equipo",  # Generic name for the notification record
                    },
                )

                Notificacion.objects.create(
                    documento=self.doc,
                    revision_obj=self.object,
                    destinatarios=", ".join(
                        [p.user.email for p in destinatarios if p.user.email]
                    ),
                    tipo="U",  # Urgente
                    asunto=asunto,
                    cuerpo_html=mensaje_html_para_notificacion,
                )
                messages.success(
                    self.request, "Revisión guardada y notificación urgente enviada."
                )
            else:
                messages.warning(
                    self.request,
                    "Revisión guardada, pero no se encontraron destinatarios para la notificación urgente.",
                )
        else:
            messages.success(self.request, "Revisión guardada correctamente.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("docs:detalle", args=(self.doc.id,))


def get_notification_recipients_count(request):
    if request.method == "GET":
        count = Profile.objects.filter(
            recibe_notificaciones=True, user__email__isnull=False
        ).count()
        return JsonResponse({"count": count})
    return JsonResponse({"count": 0})


class ProcesoList(DetailView):
    """Lista de documentos por proceso."""

    model = Proceso
    context_object_name = "proceso"


class ProcessAdd(CreateView):
    """Formulario para agregar un nuevo proceso."""

    model = Proceso
    form_class = ProcesoForm
    template_name = "docs/proceso_form.html"
    success_url = reverse_lazy("docs:setup")

    def get_success_url(self):
        """Permite regresar al formulario de documentos si se solicita."""
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url:
            return next_url
        return super().get_success_url()


class TipoAdd(CreateView):
    """Formulario para agregar un nuevo tipo de documento."""

    model = Tipo
    form_class = TipoForm
    template_name = "docs/tipo_form.html"
    success_url = reverse_lazy("docs:setup")

    def get_success_url(self):
        """Permite regresar al formulario de documentos si se solicita."""
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url:
            return next_url
        return super().get_success_url()


class Buscador(HTMXDocumentListMixin, ListView):
    """Vista para el buscador de documentos."""

    template_name = "docs/list.html"
    context_object_name = "docs"
    list_title = "Resultados de búsqueda"
    list_description = "Documentos que coinciden con tu búsqueda."

    def get_queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        if not query:
            return Documento.objects.none()
        resultados = watson.search(query)
        ids = []
        for resultado in resultados:
            obj = getattr(resultado, "object", None)
            if isinstance(obj, Documento):
                ids.append(obj.id)
        if not ids:
            ids = list(
                Documento.objects.filter(
                    Q(nombre__icontains=query) | Q(texto_ayuda__icontains=query)
                ).values_list("id", flat=True)
            )
        return (
            Documento.objects.filter(id__in=ids, activo=True)
            .select_related("proceso", "tipo")
            .prefetch_related("revision_set")
            .order_by("proceso", "nombre")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context


class PanicButtonView(FormView):
    """Vista para el botón de pánico."""

    template_name = "docs/panic.html"
    form_class = ReporteForm

    def get_context_data(self, **kwargs):
        """Agregamos el documento_id obtenido mediante el parámetro
        pk de la URL al contexto de la vista."""
        context = super(PanicButtonView, self).get_context_data(**kwargs)
        context["documento"] = Documento.objects.get(pk=self.kwargs["pk"])
        return context

    def get_initial(self):
        """Inicializamos el formulario con el documento actual
        para usarlo en el templates y el registro que se guarda
        en la base de datos."""
        initial = super(PanicButtonView, self).get_initial()
        initial["documento"] = self.kwargs["pk"]
        return initial

    # Guardamos el reporte en la base de datos
    def form_valid(self, form):
        """El Documento en el contexto se agrega al campo documento
        del formulario."""
        form.instance.documento = Documento.objects.get(pk=self.kwargs["pk"])
        # Si el correo no termina en '@ine.mx' se rechaza el formulario
        if not form.instance.correo.endswith("@ine.mx"):
            return self.form_invalid(form)
        # Si el formulario es válido, se guarda en la base de datos
        else:
            form.save()
        return super(PanicButtonView, self).form_valid(form)

    # Redirigimos a la página de éxito
    def get_success_url(self):
        return reverse_lazy("docs:panic_success")


class ReportesList(ListView):
    """Lista de reportes."""

    model = Reporte
    template_name = "docs/panic_reportes.html"

    # Agregamos los reportes al contexto de la vista
    def get_context_data(self, **kwargs):
        context = super(ReportesList, self).get_context_data(**kwargs)
        context["pendientes"] = Reporte.objects.filter(resuelto=False).order_by(
            "-created"
        )
        context["resueltos"] = Reporte.objects.filter(resuelto=True).order_by(
            "-resuelto_en"
        )
        return context


class NotificacionListView(LoginRequiredMixin, ListView):
    model = Notificacion
    template_name = "docs/notificacion_list.html"
    context_object_name = "notificaciones"
    ordering = ["-fecha_envio"]


class NotificacionDetailView(LoginRequiredMixin, DetailView):
    model = Notificacion
    template_name = "docs/notificacion_detail.html"
    context_object_name = "notificacion"


class PanicResolve(LoginRequiredMixin, UpdateView):
    model = Reporte
    template_name = "docs/panic_resolve.html"
    success_url = reverse_lazy("docs:panic_reportes")
    form_class = PanicResolveForm

    # Agregamos el reporte al contexto de la vista
    def get_context_data(self, **kwargs):
        context = super(PanicResolve, self).get_context_data(**kwargs)
        context["reporte"] = Reporte.objects.get(pk=self.kwargs["pk"])
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        self.object = form.save(commit=False)
        self.object.documento = Reporte.objects.get(pk=self.kwargs["pk"]).documento
        self.object.resuelto_por = self.request.user
        self.object.resuelto_en = datetime.now()
        self.object.resolucion = form.cleaned_data["resolucion"]
        self.object.resuelto = form.cleaned_data["resuelto"]
        self.object.save()
        return super().form_valid(form)


# reportes_context - un custom context processor para agregar el conteo de reportes
# a todas las vistas
def reportes_context(request):
    if request.user.is_authenticated:
        reportes = Reporte.objects.filter(resuelto=False).count()
        return {"panic_reports": reportes}
    else:
        return {}


class CMIMovilView(TemplateView):
    """Vista de ayuda para el CMI Móvil."""

    template_name = "docs/CMIMovil_help.html"
