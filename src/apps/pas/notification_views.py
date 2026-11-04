from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from apps.profiles.models import Profile
from .models import CalendarioNotificaciones
from .notification_forms import AgendaCorreoForm, CalendarioCorreoForm
from .notification_permissions import es_cabecera


@login_required
@require_http_methods(["GET", "POST"])
def agenda_correo(request):
    perfil = get_object_or_404(Profile, user=request.user)
    obligatoria = es_cabecera(request.user)
    form = None if obligatoria else AgendaCorreoForm(
        request.POST if request.method == "POST" else None, instance=perfil,
    )
    if request.method == "POST" and form and form.is_valid():
        form.save()
        messages.success(request, "Preferencia de agenda guardada.")
        return redirect("pas:agenda-correo")
    return render(request, "pas/notificaciones_config.html", {
        "form": form, "titulo": "Mi agenda por correo", "obligatoria": obligatoria,
        "admin_calendario": request.user.has_perm("pas.change_calendarionotificaciones"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def calendario_correo(request):
    if not request.user.has_perm("pas.change_calendarionotificaciones"):
        raise PermissionDenied
    config = CalendarioNotificaciones.objects.filter(pk=1).first() or CalendarioNotificaciones()
    form = CalendarioCorreoForm(request.POST if request.method == "POST" else None, instance=config)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Calendario de envíos actualizado.")
        return redirect("pas:calendario-correo")
    return render(request, "pas/notificaciones_config.html", {
        "form": form, "titulo": "Calendario de correos PM²", "calendario": True,
    })
