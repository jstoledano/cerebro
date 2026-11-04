from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.docs.models import Revision
from apps.pmml.delivery import enviar, enviar_prueba
from apps.pmml.models import EnvioCorreo
from apps.pmml.weekly import destinatarios, contenido, preparar_envios, archivar_aceptado, completar_revisiones


class Command(BaseCommand):
    help = "Notificaciones documentales pendientes, con resultado por destinatario."

    def add_arguments(self, parser):
        parser.add_argument("--prueba", action="store_true", help="Una sola muestra al correo de prueba.")
        parser.add_argument("--simular", action="store_true")
        parser.add_argument("--reintentar-fallidos", action="store_true")

    def handle(self, *args, **options):
        correos, invalidos = destinatarios()
        revisiones = list(Revision.objects.filter(
            notificacion_enviada=False, notificacion_urgente=False,
        ).select_related("documento").order_by("pk"))
        self.stdout.write(f"Suscriptores válidos={len(correos)}; inválidos={invalidos}; revisiones pendientes={len(revisiones)}")
        if not revisiones:
            return
        if options["prueba"]:
            payload = contenido(revisiones)
            count = enviar_prueba(payload["asunto"], payload["texto"], payload["html"], "Suscriptores activos de PMML")
            self.stdout.write(f"Muestras aceptadas por SMTP={count}. Sin cambios en revisiones ni suscripciones.")
            return
        modo = getattr(settings, "NOTIFICACIONES_MODO", "simular")
        if modo not in {"simular", "produccion"}:
            raise CommandError("NOTIFICACIONES_MODO debe ser simular o produccion.")
        if options["simular"] or modo != "produccion":
            for email in correos:
                self.stdout.write(f"SIMULADO destinatario={email}")
            return
        if not correos:
            raise CommandError("No hay suscriptores activos con correo válido; revisiones conservadas pendientes.")
        incidencias = len(invalidos)
        for pk in sorted(preparar_envios(correos)):
            envio = EnvioCorreo.objects.get(pk=pk)
            estado = enviar(envio, reintentar=options["reintentar_fallidos"])
            self.stdout.write(f"envio={pk} destinatario={envio.destinatario} estado={estado} message_id={envio.message_id}")
            if estado == EnvioCorreo.Estado.ACEPTADO:
                archivar_aceptado(pk)
            else:
                incidencias += 1
        if not invalidos:
            completar_revisiones(correos)
        if incidencias:
            raise CommandError(f"{incidencias} incidencias. Consulte el registro de envíos antes de reintentar.")
