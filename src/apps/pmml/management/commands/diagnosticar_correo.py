"""Diagnóstico local sin envío ni modificación de suscripciones."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.pas.notification_permissions import recibe_agenda
from apps.pmml.models import Subscriber, EnvioCorreo
from apps.docs.models import Revision
from apps.pmml.delivery import correo_valido


class Command(BaseCommand):
    help = "Inspecciona usuario, suscripción PMML y estado SMTP de un correo, sin enviar."

    def add_arguments(self, parser):
        parser.add_argument("correo")

    def handle(self, *args, **options):
        email = options["correo"].strip().lower()
        self.stdout.write(f"Correo válido={correo_valido(email)}")
        for user in get_user_model().objects.filter(email__iexact=email).select_related("profile__unidad_organizacional"):
            profile = getattr(user, "profile", None)
            self.stdout.write(f"Usuario={user.pk}; activo={user.is_active}; agenda={recibe_agenda(user)}")
        subscribers = Subscriber.objects.filter(Q(usuario_inst__iexact=email.split('@')[0]) | Q(usuario_inst__iexact=email))
        if not subscribers.exists():
            self.stdout.write("PMML: sin suscripción registrada. El correo semanal solo incluye suscriptores activos.")
        for subscriber in subscribers:
            self.stdout.write(f"PMML id={subscriber.pk}; activo={subscriber.is_active}; destino={subscriber.email_full}")
        self.stdout.write(f"Revisiones semanales pendientes={Revision.objects.filter(notificacion_enviada=False, notificacion_urgente=False).count()}")
        for envio in EnvioCorreo.objects.filter(destinatario__iexact=email)[:10]:
            self.stdout.write(f"Envío={envio.pk}; tipo={envio.tipo}; fecha={envio.fecha}; estado={envio.estado}; intentos={envio.intentos}; Message-ID={envio.message_id}; error={envio.error}")
        self.stdout.write("Aceptado por SMTP significa aceptación por el proveedor. Para confirmar entrega o rechazo del INE, consulte sus eventos usando destinatario y Message-ID.")
