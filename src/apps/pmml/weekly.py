"""Notificaciones documentales con seguimiento por revisión y destinatario."""
import uuid
from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from apps.docs.models import Revision, Notificacion, EntregaRevision
from .models import Subscriber, EnvioCorreo
from .delivery import correo_valido, enviar


def destinatarios():
    validos = set()
    invalidos = []
    for subscriber in Subscriber.objects.filter(is_active=True).order_by("pk"):
        email = subscriber.email_full
        if correo_valido(email):
            validos.add(email)
        else:
            invalidos.append(subscriber.pk)
    return sorted(validos), invalidos


def contenido(revisiones):
    context = {"revisiones": revisiones, "fecha_notificacion": timezone.localdate(),
               "site_url": settings.SITE_URL.rstrip("/")}
    return {
        "asunto": f"CMI — Documentos actualizados al {timezone.localdate():%d/%m/%Y}",
        "html": render_to_string("docs/notificacion_periodica.html", context),
        "texto": render_to_string("docs/notificacion_periodica.txt", {
            **context, "filas": [{"nombre": r.documento.nombre, "numero": r.revision,
                                  "cambios": strip_tags(r.cambios), "url": context["site_url"] + r.get_absolute_url()}
                                 for r in revisiones],
        }),
    }


def preparar_envios(correos):
    ids = set()
    # PostgreSQL serializa dos ejecuciones concurrentes sobre las mismas revisiones.
    with transaction.atomic():
        revisiones = list(Revision.objects.select_for_update().filter(
            notificacion_enviada=False, notificacion_urgente=False,
        ).select_related("documento").order_by("pk"))
        for email in correos:
            entregas = list(EntregaRevision.objects.filter(revision__in=revisiones, destinatario=email))
            ids.update(entrega.envio_id for entrega in entregas)
            asignadas = {entrega.revision_id for entrega in entregas}
            nuevas = [r for r in revisiones if r.pk not in asignadas]
            if nuevas:
                envio = EnvioCorreo.objects.create(
                    clave=f"documentos:{uuid.uuid4()}", tipo="documentos", fecha=timezone.localdate(),
                    destinatario=email, **contenido(nuevas),
                )
                EntregaRevision.objects.bulk_create([
                    EntregaRevision(revision=r, destinatario=email, envio=envio) for r in nuevas
                ])
                ids.add(envio.pk)
    return ids


def archivar_aceptado(envio_id):
    with transaction.atomic():
        envio = EnvioCorreo.objects.select_for_update().get(pk=envio_id)
        if envio.estado == EnvioCorreo.Estado.ACEPTADO and not envio.documentado:
            Notificacion.objects.create(
                tipo=Notificacion.Tipo.SEMANAL, asunto=envio.asunto,
                cuerpo_html=envio.html, destinatarios=envio.destinatario,
            )
            envio.documentado = True
            envio.save(update_fields=["documentado", "actualizado"])


def completar_revisiones(correos):
    if not correos:
        return
    for revision in Revision.objects.filter(notificacion_enviada=False, notificacion_urgente=False):
        aceptados = set(revision.entregas_correo.filter(
            envio__estado=EnvioCorreo.Estado.ACEPTADO,
        ).values_list("destinatario", flat=True))
        if set(correos) <= aceptados:
            Revision.objects.filter(pk=revision.pk, notificacion_enviada=False).update(
                notificacion_enviada=True, fecha_notificacion=timezone.now(),
            )
