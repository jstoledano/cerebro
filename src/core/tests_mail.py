"""Pruebas de agenda por correo, configuración y entregas documentales.

Todos los mensajes se capturan en memoria. No hay conexiones SMTP reales.
"""
import datetime
import io
import smtplib
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.test import TestCase, Client, override_settings
from apps.profiles.models import UnidadOrganizacional
from apps.pas.models import Plan, Accion, CicloActividad, Ejecucion, CalendarioNotificaciones
from apps.pas.notifications import crear_resumen
from apps.pas.notification_permissions import recibe_agenda
from apps.pas.notification_forms import CalendarioCorreoForm
from apps.pmml.models import Subscriber, EnvioCorreo
from apps.pmml.delivery import enviar
from apps.docs.models import Tipo, Proceso, Documento, Revision, EntregaRevision, Notificacion
from core.notification_schedule import validar_dias

HOY = datetime.date(2026, 11, 2)  # Lunes.
User = get_user_model()


class MailTests(TestCase):
    def setUp(self):
        self.clock = patch("django.utils.timezone.localdate", return_value=HOY)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.unit = UnidadOrganizacional.objects.create(clave="50", nombre="Vocalía del RFE", site=0)
        self.sub = UnidadOrganizacional.objects.create(clave="5010", nombre="Operación", site=0, superior=self.unit)
        self.boss = self.user("jefa", "eileen.zacaula@ine.mx", self.unit)
        self.operator = self.user("javier", "javier.sanchezt@ine.mx", self.sub)
        self.plan = Plan.objects.create(nombre="Plan RFE", documento=4)

    def user(self, name, email, unit=None):
        user = User.objects.create_user(username=name, email=email, password="test", first_name=name)
        user.profile.unidad_organizacional = unit
        user.profile.save()
        return user

    def task(self, days=0, user=None, completed=False, priority="normal", name="Entregar informe"):
        due = HOY + datetime.timedelta(days=days)
        action = Accion.objects.create(plan=self.plan, accion=name, puesto_responsable="50",
            responsable=user or self.operator, prioridad=priority, periodicidad="unica",
            fecha_inicio=due, fecha_fin=due, evidencia="Informe de resultados firmado")
        cycle = CicloActividad.objects.create(accion=action, numero=1, fecha_inicio=due, fecha_fin=due)
        return Ejecucion.objects.create(ciclo=cycle, ambito="JL", responsable=user or self.operator, completada=completed)

    def run_agenda(self, *args):
        output = io.StringIO()
        call_command("notificar_agenda", *args, stdout=output)
        return output.getvalue()

    def document_revision(self, number=1):
        tipo, _ = Tipo.objects.get_or_create(tipo="Manual", slug="manual")
        proc, _ = Proceso.objects.get_or_create(proceso="SGC", slug="sgc")
        doc, _ = Documento.objects.get_or_create(nombre="Manual de prueba", tipo=tipo, proceso=proc, autor=self.operator)
        return Revision.objects.create(documento=doc, revision=number, f_actualizacion=HOY,
                                       cambios="<p>Cambio documentado</p>", autor=self.operator)

    def subscribe(self, username):
        return Subscriber.objects.create(nombre_completo=username, usuario_inst=username, is_active=True)

    def test_x0_default_and_other_opt_in(self):
        for clave in ("00", "10", "20", "30"):
            unit = UnidadOrganizacional.objects.create(clave=clave, nombre=clave, site=0)
            self.assertTrue(recibe_agenda(self.user("u" + clave, clave + "@ine.mx", unit)))
        self.assertTrue(recibe_agenda(self.boss))
        self.assertFalse(recibe_agenda(self.operator))
        self.operator.profile.recibe_notificaciones = True
        self.operator.profile.save()
        self.assertTrue(recibe_agenda(self.operator))

    def test_inactive_cabecera_not_recipient(self):
        self.boss.is_active = False
        self.assertFalse(recibe_agenda(self.boss))
        self.boss.is_active = True
        self.unit.activa = False
        self.unit.save()
        boss = User.objects.get(pk=self.boss.pk)
        self.assertFalse(recibe_agenda(boss))

    def test_agenda_contains_three_sections_and_scoped_tasks(self):
        self.task(-1, name="Atrasada")
        self.task(3, name="Próxima")
        self.task(10, name="Vigilancia")
        other_unit = UnidadOrganizacional.objects.create(clave="20", nombre="Otra", site=0)
        other = self.user("otro", "otro@ine.mx", other_unit)
        e = self.task(0, user=other, name="Ajena")
        e.accion.puesto_responsable = "20"
        e.accion.save()
        result = crear_resumen(self.boss, HOY)
        for text in ("Alarma", "Faro", "Radar", "Atrasada", "Próxima", "Vigilancia"):
            self.assertIn(text, result["texto"])
        self.assertNotIn("Ajena", result["texto"])

    def test_operational_due_and_overdue_only(self):
        self.task(-2, name="Atrasada")
        self.task(0, name="Hoy")
        self.task(1, name="Mañana")
        self.task(-1, completed=True, name="Concluida")
        result = crear_resumen(self.operator, HOY)
        self.assertIn("Atrasada", result["texto"])
        self.assertIn("Hoy", result["texto"])
        self.assertNotIn("Mañana", result["texto"])
        self.assertNotIn("Concluida", result["texto"])
        self.assertEqual(result["responder_a"], [self.boss.email])
        self.assertIn("Informe de resultados firmado", result["texto"])

    def test_closed_plan_has_no_operational_notices(self):
        self.task()
        self.plan.eliminacion = True
        self.plan.save()
        self.assertIsNone(crear_resumen(self.operator, HOY))

    def test_empty_agenda_is_omitted(self):
        self.assertIsNone(crear_resumen(self.boss, HOY))

    def test_weekend_default_and_global_selection(self):
        self.task(-1)
        saturday = HOY + datetime.timedelta(days=5)
        self.assertIsNone(crear_resumen(self.operator, saturday))
        CalendarioNotificaciones.objects.create(dias=[5, 6])
        self.assertIsNotNone(crear_resumen(self.operator, saturday))
        self.assertIsNone(crear_resumen(self.operator, HOY))

    def test_reject_invalid_days(self):
        for days in ([], [7], [-1], [0, 0], [True], "lunes"):
            with self.subTest(days=days), self.assertRaises(ValidationError):
                validar_dias(days)
        self.assertFalse(CalendarioCorreoForm(data={"dias": ["7"]}).is_valid())

    def test_html_escapes_task_name(self):
        self.task(name='Informe & "resultados" <script>alert(1)</script>')
        result = crear_resumen(self.operator, HOY)
        self.assertNotIn("<script>", result["html"])
        self.assertIn("&amp;", result["html"])
        self.assertIn("http://testserver/pas/executions/", result["html"])

    def test_default_simulation_has_no_messages_or_ledger(self):
        self.task()
        self.run_agenda()
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EnvioCorreo.objects.exists())

    def test_preview_only_javier_no_production_marks(self):
        self.task()
        self.run_agenda("--prueba", "--usuario", self.boss.email)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["javier.sanchezt@ine.mx"])
        self.assertEqual(message.cc + message.bcc + message.reply_to, [])
        self.assertIn(self.boss.email, message.body)
        self.assertFalse(EnvioCorreo.objects.exists())

    def test_preview_requires_single_user(self):
        with self.assertRaises(CommandError):
            self.run_agenda("--prueba")

    @override_settings(NOTIFICACIONES_MODO="produccion")
    def test_one_message_per_person_per_day_and_new_day(self):
        self.task(-1)
        self.operator.profile.recibe_notificaciones = True
        self.operator.profile.save()
        self.run_agenda()
        self.run_agenda()
        self.assertEqual(len(mail.outbox), 2)
        with patch("django.utils.timezone.localdate", return_value=HOY + datetime.timedelta(days=1)):
            self.run_agenda()
        self.assertEqual(len(mail.outbox), 4)

    @override_settings(NOTIFICACIONES_MODO="produccion")
    def test_invalid_and_inactive_addresses_excluded(self):
        self.task()
        self.boss.email = "invalid"
        self.boss.save()
        self.operator.is_active = False
        self.operator.save()
        self.run_agenda()
        self.assertEqual(len(mail.outbox), 0)

    def test_calendar_admin_only(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.post("/pas/agenda/calendario-correo/", {"dias": ["6"]}).status_code, 403)
        self.operator.is_superuser = True
        self.operator.save()
        self.assertEqual(self.client.post("/pas/agenda/calendario-correo/", {"dias": ["5", "6"]}).status_code, 302)
        self.assertEqual(CalendarioNotificaciones.dias_envio(), [5, 6])

    def test_empty_calendar_shows_error_and_preserves_saved_days(self):
        self.operator.is_superuser = True
        self.operator.save()
        self.client.force_login(self.operator)
        CalendarioNotificaciones.objects.create(dias=[0, 1, 2, 3, 4])
        response = self.client.post("/pas/agenda/calendario-correo/", {})
        self.assertContains(response, "Selecciona al menos un día de envío.")
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'action="/pas/agenda/calendario-correo/"')
        self.assertContains(response, "No se guardaron los cambios.")
        self.assertEqual(CalendarioNotificaciones.dias_envio(), [0, 1, 2, 3, 4])

    def test_personal_switch_only_own_profile(self):
        self.client.force_login(self.operator)
        self.client.post("/pas/agenda/correo/", {"recibe_notificaciones": "on", "user": self.boss.pk})
        self.operator.profile.refresh_from_db()
        self.boss.profile.refresh_from_db()
        self.assertTrue(self.operator.profile.recibe_notificaciones)
        self.assertFalse(self.boss.profile.recibe_notificaciones)

    def test_cabecera_cannot_disable_agenda(self):
        self.client.force_login(self.boss)
        self.assertEqual(self.client.post("/pas/agenda/correo/", {}).status_code, 200)
        self.assertTrue(recibe_agenda(User.objects.get(pk=self.boss.pk)))

    def test_config_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.operator)
        self.assertEqual(client.post("/pas/agenda/correo/", {"recibe_notificaciones": "on"}).status_code, 403)

    def envelope(self):
        return EnvioCorreo.objects.create(clave="test", destinatario=self.operator.email, tipo="agenda",
            fecha=HOY, asunto="Prueba", texto="Texto", html="<p>Texto</p>")

    def test_delivery_is_idempotent(self):
        envio = self.envelope()
        enviar(envio)
        enviar(envio)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(envio.intentos, 1)

    def test_in_progress_blocks_concurrent_sender(self):
        envio = self.envelope()
        envio.estado = EnvioCorreo.Estado.ENVIANDO
        envio.save()
        enviar(envio, reintentar=True)
        self.assertEqual(len(mail.outbox), 0)

    def test_uncertain_delivery_not_retried(self):
        envio = self.envelope()
        with patch("django.core.mail.EmailMultiAlternatives.send", side_effect=ConnectionResetError("SMTP desconectado")):
            self.assertEqual(enviar(envio), EnvioCorreo.Estado.INCIERTO)
        enviar(envio, reintentar=True)
        self.assertEqual(len(mail.outbox), 0)

    def test_rejected_delivery_explicit_retry(self):
        envio = self.envelope()
        with patch("django.core.mail.EmailMultiAlternatives.send", side_effect=smtplib.SMTPRecipientsRefused({"x": (550, b"rejected")})):
            self.assertEqual(enviar(envio), EnvioCorreo.Estado.FALLIDO)
        enviar(envio)
        self.assertEqual(len(mail.outbox), 0)
        enviar(envio, reintentar=True)
        self.assertEqual(len(mail.outbox), 1)

    def test_weekly_simulation_and_preview(self):
        revision = self.document_revision()
        self.subscribe("eileen.zacaula")
        call_command("notificar_docs", stdout=io.StringIO())
        self.assertEqual(len(mail.outbox), 0)
        call_command("notificar_docs", "--prueba", stdout=io.StringIO())
        self.assertEqual(mail.outbox[0].to, ["javier.sanchezt@ine.mx"])
        revision.refresh_from_db()
        self.assertFalse(revision.notificacion_enviada)
        self.assertFalse(EntregaRevision.objects.exists())

    @override_settings(NOTIFICACIONES_MODO="produccion")
    def test_weekly_partial_failure_retries_only_failed_recipient(self):
        revision = self.document_revision()
        self.subscribe("eileen.zacaula")
        self.subscribe("javier.sanchezt")
        original = mail.EmailMultiAlternatives.send
        def fail_eileen(message, **kwargs):
            if message.to == [self.boss.email]:
                raise smtplib.SMTPRecipientsRefused({self.boss.email: (550, b"refused")})
            return original(message, **kwargs)
        with patch("django.core.mail.EmailMultiAlternatives.send", new=fail_eileen):
            with self.assertRaises(CommandError):
                call_command("notificar_docs", stdout=io.StringIO())
        revision.refresh_from_db()
        self.assertFalse(revision.notificacion_enviada)
        self.assertEqual(len(mail.outbox), 1)
        call_command("notificar_docs", "--reintentar-fallidos", stdout=io.StringIO())
        revision.refresh_from_db()
        self.assertTrue(revision.notificacion_enviada)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[-1].to, [self.boss.email])
        call_command("notificar_docs", stdout=io.StringIO())
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(Notificacion.objects.count(), 2)

    @override_settings(NOTIFICACIONES_MODO="produccion")
    def test_weekly_inactive_subscriber_excluded(self):
        self.document_revision()
        self.subscribe("javier.sanchezt")
        Subscriber.objects.create(nombre_completo="Inactiva", usuario_inst="eileen.zacaula")
        call_command("notificar_docs", stdout=io.StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.operator.email])

    def test_full_address_in_subscription_does_not_duplicate_domain(self):
        subscriber = self.subscribe("EILEEN.ZACAULA@ine.mx")
        self.assertEqual(subscriber.email_full, "eileen.zacaula@ine.mx")

    def test_diagnostics_do_not_send_or_activate(self):
        self.subscribe("javier.sanchezt")
        output = io.StringIO()
        call_command("diagnosticar_correo", self.boss.email, stdout=output)
        self.assertIn("sin suscripción", output.getvalue())
        self.assertEqual(len(mail.outbox), 0)
