"""Entrega con exclusión concurrente y resultados de SMTP auditables."""
import logging
import smtplib
from email.utils import make_msgid, parseaddr

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db.models import F
from django.utils import timezone

from .models import EnvioCorreo

logger = logging.getLogger(__name__)


def correo_valido(email):
    try:
        validate_email(email or "")
        return True
    except ValidationError:
        return False


def enviar(envio, reintentar=False):
    """Reserva atómica antes de SMTP. Los estados inciertos nunca se reenvían solos."""
    estados = [EnvioCorreo.Estado.PENDIENTE]
    if reintentar:
        estados.append(EnvioCorreo.Estado.FALLIDO)
    domain = parseaddr(settings.DEFAULT_FROM_EMAIL)[1].rsplit("@", 1)[-1]
    message_id = envio.message_id or make_msgid(domain=domain)
    reservado = EnvioCorreo.objects.filter(pk=envio.pk, estado__in=estados).update(
        estado=EnvioCorreo.Estado.ENVIANDO, intentos=F("intentos") + 1,
        actualizado=timezone.now(), message_id=message_id,
    )
    if not reservado:
        envio.refresh_from_db()
        return envio.estado
    try:
        message = EmailMultiAlternatives(
            envio.asunto, envio.texto, settings.DEFAULT_FROM_EMAIL, [envio.destinatario],
            reply_to=envio.responder_a, headers={"Message-ID": message_id},
        )
        message.attach_alternative(envio.html, "text/html")
        cantidad = message.send(fail_silently=False)
        estado = EnvioCorreo.Estado.ACEPTADO if cantidad == 1 else EnvioCorreo.Estado.FALLIDO
        error = "" if cantidad == 1 else "El backend no confirmó ningún mensaje enviado."
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused,
            smtplib.SMTPDataError, smtplib.SMTPAuthenticationError) as exc:
        estado, error = EnvioCorreo.Estado.FALLIDO, str(exc)
    except Exception as exc:
        # Una desconexión después de DATA puede ocurrir tras la aceptación remota.
        estado, error = EnvioCorreo.Estado.INCIERTO, str(exc)
    EnvioCorreo.objects.filter(pk=envio.pk).update(
        estado=estado, error=error[:2000], actualizado=timezone.now(),
        aceptado_en=timezone.now() if estado == EnvioCorreo.Estado.ACEPTADO else None,
    )
    envio.refresh_from_db()
    logger.info("Correo id=%s tipo=%s destinatario=%s estado=%s message_id=%s",
                envio.pk, envio.tipo, envio.destinatario, estado, message_id)
    return estado


def enviar_prueba(asunto, texto, html, destinatario_original):
    """Un solo destinatario de prueba, sin CC/BCC/Reply-To ni marcas de producción."""
    destino = settings.NOTIFICACIONES_CORREO_PRUEBA
    if not correo_valido(destino):
        raise ValueError("El correo de prueba no es válido.")
    prefijo = f"PRUEBA. Destinatario previsto: {destinatario_original}\n\n"
    message = EmailMultiAlternatives(
        "[PRUEBA] " + asunto, prefijo + texto, settings.DEFAULT_FROM_EMAIL, [destino],
    )
    from django.utils.html import format_html
    message.attach_alternative(str(format_html("<p>{}</p>", prefijo)) + html, "text/html")
    return message.send(fail_silently=False)
