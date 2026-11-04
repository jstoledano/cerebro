from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.pas.models import CalendarioNotificaciones
from django.utils import timezone
from apps.pmml.delivery import correo_valido, enviar, enviar_prueba
from apps.pmml.models import EnvioCorreo
from apps.pas.notifications import crear_resumen, preparar_recurrencias


class Command(BaseCommand):
    help = "Agenda y recordatorios del día. Simula salvo NOTIFICACIONES_MODO=produccion."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", help="Correo exacto del usuario cuya agenda se procesa.")
        parser.add_argument("--prueba", action="store_true", help="Una muestra al correo de prueba; requiere --usuario.")
        parser.add_argument("--simular", action="store_true")
        parser.add_argument("--reintentar-fallidos", action="store_true")

    def handle(self, *args, **options):
        if options["prueba"] and not options["usuario"]:
            raise CommandError("Use --prueba --usuario CORREO para enviar una sola muestra.")
        modo = getattr(settings, "NOTIFICACIONES_MODO", "simular")
        if modo not in {"simular", "produccion"}:
            raise CommandError("NOTIFICACIONES_MODO debe ser simular o produccion.")
        real = modo == "produccion" and not options["prueba"] and not options["simular"]
        hoy = timezone.localdate()
        if hoy.weekday() not in CalendarioNotificaciones.dias_envio():
            self.stdout.write("Día sin envío según el calendario de PM².")
            return
        usuarios = get_user_model().objects.filter(is_active=True).select_related("profile__unidad_organizacional")
        if options["usuario"]:
            usuarios = usuarios.filter(email__iexact=options["usuario"])
            if usuarios.count() != 1:
                raise CommandError("El correo debe identificar exactamente un usuario activo.")
        total = enviados = incidencias = 0
        # La simulación revierte incluso la materialización de recurrencias.
        with transaction.atomic():
            preparar_recurrencias()
            payloads = []
            for user in usuarios:
                if not correo_valido(user.email):
                    self.stdout.write(f"OMITIDO usuario={user.pk}: correo ausente o inválido")
                    continue
                resumen = crear_resumen(user, hoy)
                if resumen:
                    payloads.append((user.pk, user.email.strip().lower(), resumen))
            if not real:
                transaction.set_rollback(True)
        for user_id, email, resumen in payloads:
            total += 1
            if options["prueba"]:
                enviados += enviar_prueba(resumen["asunto"], resumen["texto"], resumen["html"], email)
            elif real:
                envio, _ = EnvioCorreo.objects.get_or_create(
                    clave=f"agenda:{hoy.isoformat()}:{user_id}",
                    defaults={"destinatario": email, "tipo": "agenda", "fecha": hoy, **resumen},
                )
                estado = enviar(envio, reintentar=options["reintentar_fallidos"])
                self.stdout.write(f"usuario={user_id} correo={email} estado={estado} envio={envio.pk}")
                enviados += estado == EnvioCorreo.Estado.ACEPTADO
                incidencias += estado not in {EnvioCorreo.Estado.ACEPTADO}
            else:
                self.stdout.write(f"SIMULADO usuario={user_id} correo={email} asunto={resumen['asunto']}")
        self.stdout.write(f"Resúmenes={total}; aceptados SMTP={enviados}; incidencias={incidencias}")
        if incidencias:
            raise CommandError("Existen envíos pendientes de revisión; consulte EnvioCorreo.")
