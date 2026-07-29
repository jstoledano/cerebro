import os
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.docs.models import Notificacion, Revision
from apps.pmml.models import Subscriber

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Envía notificaciones programadas para revisiones de documentos no urgentes."

    def handle(self, *args, **options):
        ahora = timezone.localtime()

        revisiones_pendientes = Revision.objects.filter(notificacion_enviada=False)

        if not revisiones_pendientes.exists():
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{ahora.strftime('%Y-%m-%d %H:%M')}] No hay revisiones pendientes de notificación."
                )
            )
            return

        destinatarios = Subscriber.objects.filter(is_active=True)

        if not destinatarios.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"[{ahora.strftime('%Y-%m-%d %H:%M')}] No se encontraron suscriptores activos para las notificaciones."
                )
            )
            return

        context = {
            "revisiones": revisiones_pendientes,
            "fecha_notificacion": ahora.strftime("%d/%b/%Y"),
            "site_url": settings.SITE_URL,
        }

        asunto = f"Documentos actualizados a la fecha {context['fecha_notificacion']}"
        mensaje_html = render_to_string("docs/notificacion_periodica.html", context)

        smtp_user = os.getenv("SMTP_USER")
        from_email = f"SGC Tlaxcala <{smtp_user}>"

        if not smtp_user:
            logger.critical(
                f"[{ahora.strftime('%Y-%m-%d %H:%M')}] No se encontró la variable de entorno SMTP_USER. No se pueden enviar notificaciones."
            )
            self.stdout.write(self.style.ERROR("Error: SMTP_USER no configurada."))
            return

        texto_plano = (
            "Se han actualizado documentos en el sistema CMI.\n\n"
            "Puede revisar los cambios ingresando al sistema.\n\n"
            "Saludos,\n"
            "Equipo CMI"
        )

        for subscriber in destinatarios:
            to_email = subscriber.email_full

            try:
                send_mail(
                    asunto,
                    texto_plano,
                    from_email,
                    [to_email],
                    html_message=mensaje_html,
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(
                    f"[{ahora.strftime('%Y-%m-%d %H:%M')}] Error al enviar notificación a {subscriber.email_full}: {e}"
                )
                self.stdout.write(
                    self.style.ERROR(
                        f"Error al enviar notificación a {subscriber.email_full}: {e}"
                    )
                )

        for revision in revisiones_pendientes:
            revision.fecha_notificacion = ahora
            revision.notificacion_enviada = True
            revision.save()

        cuerpo_html_para_notificacion = render_to_string(
            "docs/notificacion_periodica_content.html", context
        )
        Notificacion.objects.create(
            documento=None,
            revision_obj=None,
            destinatarios=", ".join([s.email_full for s in destinatarios]),
            tipo=Notificacion.Tipo.SEMANAL,
            asunto=asunto,
            cuerpo_html=cuerpo_html_para_notificacion,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"[{ahora.strftime('%Y-%m-%d %H:%M')}] Notificaciones programadas enviadas a {destinatarios.count()} suscriptores."
            )
        )
