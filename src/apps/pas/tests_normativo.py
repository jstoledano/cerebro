"""Regresiones de permisos jerárquicos, filtros y auditoría (issue 138)."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.profiles.models import UnidadOrganizacional
from .models import Accion, CicloActividad, Ejecucion, Evidencia, EventoEvidencia, Plan
from .permissions import ejecuciones_gestionables, usuario_puede_gestionar_evidencia
from .tests import EvidenciasFixtureMixin

User = get_user_model()


class PASNormativoTests(EvidenciasFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.evidence.fecha = timezone.localdate()
        self.evidence.save()
        self.unidad = UnidadOrganizacional.objects.create(clave="50", nombre="Normativo", site=0)
        self.local = UnidadOrganizacional.objects.create(clave="5011", nombre="Operativo local", superior=self.unidad, site=0)
        self.distrital = UnidadOrganizacional.objects.create(clave="51", nombre="Operativo distrital", site=1)
        otra_distrital = UnidadOrganizacional.objects.create(clave="52", nombre="Cabecera distrital", site=2)
        self.descendiente = UnidadOrganizacional.objects.create(clave="5203", nombre="Operativo indirecto", superior=otra_distrital, site=2)
        self.normativo = User.objects.create_user(username="normativo")
        self.asignar_unidad(self.normativo, self.unidad)
        self.asignar_unidad(self.user, self.local)
        self.api.force_authenticate(user=self.normativo)
        self.client.force_login(self.normativo)

    @staticmethod
    def asignar_unidad(user, unidad):
        user.profile.unidad_organizacional = unidad
        user.profile.save()

    def test_alcance_funcional_local_distrital_e_indirecto(self):
        for unidad in (self.local, self.distrital, self.descendiente):
            with self.subTest(clave=unidad.clave):
                self.asignar_unidad(self.user, unidad)
                for operacion in ("crear", "editar", "eliminar"):
                    self.assertTrue(usuario_puede_gestionar_evidencia(self.normativo, self.execution, operacion))
                self.assertFalse(usuario_puede_gestionar_evidencia(self.normativo, self.other_execution, "editar"))

    def test_actividad_normativa_no_extiende_acceso_a_todo_el_plan(self):
        self.asignar_unidad(self.user, None)
        self.action.puesto_responsable = "50"
        self.action.save()
        otra = Accion.objects.create(plan=self.plan, accion="Fuera de supervisión", responsable=self.other)
        ciclo = CicloActividad.objects.create(accion=otra, numero=1, fecha_inicio=timezone.localdate(), fecha_fin=timezone.localdate())
        fuera = Ejecucion.objects.create(ciclo=ciclo, ambito="JL", responsable=self.other)
        self.assertTrue(usuario_puede_gestionar_evidencia(self.normativo, self.other_execution, "editar"))
        self.assertFalse(usuario_puede_gestionar_evidencia(self.normativo, fuera, "editar"))

    def test_subordinado_en_otro_plan_sigue_bajo_supervision(self):
        otro_plan = Plan.objects.create(nombre="Transversal", documento=1, user=self.other)
        self.action.plan = otro_plan
        self.action.save()
        self.assertTrue(ejecuciones_gestionables(self.normativo).filter(pk=self.execution.pk).exists())

    def test_inactivos_y_unidad_inactiva_quedan_fuera(self):
        self.user.is_active = False
        self.user.save()
        self.assertFalse(usuario_puede_gestionar_evidencia(self.normativo, self.execution, "editar"))
        self.user.is_active = True
        self.user.save()
        self.local.activa = False
        self.local.save()
        self.assertFalse(usuario_puede_gestionar_evidencia(self.normativo, self.execution, "editar"))
        self.local.activa = True
        self.local.save()
        self.unidad.activa = False
        self.unidad.save()
        self.assertFalse(usuario_puede_gestionar_evidencia(self.normativo, self.execution, "editar"))

    def test_permisos_globales_no_amplian_alcance(self):
        self.normativo.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="pas", codename__in=["view_plan", "change_ejecucion", "add_evidencia", "change_evidencia", "delete_evidencia"],
        ))
        ajena = Evidencia.objects.create(ejecucion=self.other_execution, descripcion="Ajena")
        for metodo in ("get", "patch", "delete"):
            response = getattr(self.api, metodo)(f"/api/v1/pas/evidences/{ajena.pk}/")
            self.assertIn(response.status_code, (403, 404), response.data)
        for ruta in ("evidence-edit", "evidence-delete", "evidence-download"):
            self.assertIn(self.client.get(reverse("pas:" + ruta, args=[ajena.pk])).status_code, (403, 404))
        self.assertEqual(self.client.get(reverse("pas:execution-evidence", args=[self.other_execution.pk])).status_code, 404)
        response = self.api.post("/api/v1/pas/evidences/", self.datos(ejecucion=self.other_execution.pk), format="multipart")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(EventoEvidencia.objects.exists())

    def test_crud_api_audita_y_borra_archivo(self):
        response = self.api.post("/api/v1/pas/evidences/", self.datos(ejecucion=self.execution.pk), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        evidence = Evidencia.objects.get(pk=pk)
        storage, name = evidence.archivo.storage, evidence.archivo.name
        url = f"/api/v1/pas/evidences/{pk}/"
        response = self.api.patch(url, {"descripcion": "Corregida"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Evidencia.objects.filter(pk=pk).exists())
        self.assertFalse(storage.exists(name))
        eventos = EventoEvidencia.objects.filter(evidencia_id=pk)
        self.assertEqual(set(eventos.values_list("operacion", flat=True)), {"crear", "editar", "eliminar"})
        self.assertEqual(set(eventos.values_list("rol", flat=True)), {"normativo"})
        self.assertEqual(eventos.first().anterior["descripcion"], "Corregida")
        self.assertEqual(eventos.first().actor, self.normativo)

    def test_edicion_cerrada_conserva_autor_y_reemplaza_archivo(self):
        self.execution.completada = True
        self.execution.save()
        storage, name = self.evidence.archivo.storage, self.evidence.archivo.name
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api.put(
                f"/api/v1/pas/evidences/{self.evidence.pk}/",
                self.datos(ejecucion=self.execution.pk, archivo=self.archivo("reemplazo.pdf"), user=self.other.pk),
                format="multipart",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.evidence.refresh_from_db()
        self.execution.refresh_from_db()
        self.assertEqual(self.evidence.user, self.user)
        self.assertEqual(self.evidence.modificada_por, self.normativo)
        self.assertTrue(self.execution.completada)
        self.assertFalse(storage.exists(name))
        self.assertTrue(storage.exists(self.evidence.archivo.name))
        self.assertEqual(response.data["historial"][0]["anterior"]["autor"], self.user.pk)
        self.assertEqual(self.api.delete(f"/api/v1/pas/evidences/{self.evidence.pk}/").status_code, 400)

    def test_web_edita_cerrada_y_muestra_auditoria(self):
        self.execution.completada = True
        self.execution.save()
        response = self.client.post(reverse("pas:evidence-edit", args=[self.evidence.pk]), {
            "fecha": timezone.localdate().isoformat(), "descripcion": "Edición normativa",
        }, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 204)
        response = self.client.get(reverse("pas:execution-evidence", args=[self.execution.pk]))
        self.assertContains(response, "Historial de evidencias")
        self.assertContains(response, "normativo")
        self.assertTrue(response.context["can_edit_evidence"])
        self.assertFalse(response.context["can_add_evidence"])
        self.assertFalse(response.context["can_delete_evidence"])
        self.plan.eliminacion = True
        self.plan.save()
        self.assertEqual(self.client.get(reverse("pas:evidence-edit", args=[self.evidence.pk])).status_code, 409)

    def test_web_crea_confirma_elimina_y_conserva_historial(self):
        response = self.client.post(reverse("pas:execution-evidence-add", args=[self.execution.pk]), self.datos(), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 204)
        evidence = Evidencia.objects.exclude(pk=self.evidence.pk).get()
        storage, name, pk = evidence.archivo.storage, evidence.archivo.name, evidence.pk
        response = self.client.get(reverse("pas:evidence-delete", args=[pk]))
        self.assertContains(response, "Confirmar eliminación")
        self.assertTrue(Evidencia.objects.filter(pk=pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("pas:evidence-delete", args=[pk]), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(storage.exists(name))
        self.assertTrue(EventoEvidencia.objects.filter(evidencia_id=pk, operacion="eliminar").exists())
        self.assertContains(self.client.get(reverse("pas:execution-evidence", args=[self.execution.pk])), "eliminar")

    def test_fallo_auditoria_revierte_eliminacion_y_conserva_archivo(self):
        from .evidence_services import eliminar_evidencia
        storage, name = self.evidence.archivo.storage, self.evidence.archivo.name
        with self.captureOnCommitCallbacks(execute=True):
            with patch("apps.pas.evidence_services.registrar_evento", side_effect=RuntimeError("fallo")):
                with self.assertRaises(RuntimeError):
                    eliminar_evidencia(self.evidence, self.normativo)
        self.assertTrue(Evidencia.objects.filter(pk=self.evidence.pk).exists())
        self.assertTrue(storage.exists(name))

    def test_consulta_consolidada_filtros_y_aislamiento(self):
        ajena = Evidencia.objects.create(ejecucion=self.other_execution, descripcion="Ajena")
        anterior = Evidencia.objects.create(ejecucion=self.execution, descripcion="Anterior", fecha=timezone.localdate() - timedelta(days=10))
        url = "/api/v1/pas/evidences/"
        response = self.api.get(url)
        self.assertEqual({e["id"] for e in response.data}, {self.evidence.pk, anterior.pk})
        filtros = {"actividad": self.action.pk, "ejecucion": self.execution.pk, "responsable": self.user.pk, "desde": timezone.localdate().isoformat(), "hasta": timezone.localdate().isoformat()}
        response = self.api.get(url, filtros)
        self.assertEqual([e["id"] for e in response.data], [self.evidence.pk])
        response = self.client.get(reverse("pas:evidence-list"), filtros)
        self.assertEqual([e.pk for e in response.context["evidences"]], [self.evidence.pk])
        self.assertNotContains(response, ajena.descripcion)
        self.assertEqual(self.api.get(url, {"responsable": self.other.pk}).data, [])
        self.assertEqual(self.api.get(url, {"desde": "incorrecta"}).status_code, 400)
        self.assertEqual(self.api.get(url, {"estado": "inexistente"}).status_code, 400)
        self.assertEqual(self.api.get(url, {"desde": "2026-02-02", "hasta": "2026-01-01"}).status_code, 400)

    def test_estados_coinciden_con_estado_agenda(self):
        hoy = timezone.localdate()
        ciclo = self.execution.ciclo
        for estado, inicio, fin, completada in [
            ("terminada", -2, -1, True), ("vencida", -2, -1, False),
            ("inicia_hoy", 0, 0, False), ("vence_hoy", -1, 0, False),
            ("programada", 1, 2, False), ("pendiente", -1, 1, False),
        ]:
            with self.subTest(estado=estado):
                ciclo.fecha_inicio, ciclo.fecha_fin = hoy + timedelta(days=inicio), hoy + timedelta(days=fin)
                ciclo.save()
                self.execution.completada = completada
                self.execution.save()
                self.assertEqual(self.execution.estado_agenda, estado)
                response = self.api.get("/api/v1/pas/evidences/", {"estado": estado})
                self.assertEqual([e["id"] for e in response.data], [self.evidence.pk])

    def test_paginacion_conserva_total(self):
        Evidencia.objects.bulk_create([Evidencia(ejecucion=self.execution, descripcion=f"Evidencia {i}") for i in range(35)])
        ids = set()
        for pagina in (1, 2):
            response = self.client.get(reverse("pas:evidence-list"), {"page": pagina})
            self.assertEqual(response.context["paginator"].count, 36)
            ids.update(e.pk for e in response.context["evidences"])
        self.assertEqual(len(ids), 36)

    def test_operativo_con_unidad_conserva_bloqueo_de_ejecucion_cerrada(self):
        self.execution.completada = True
        self.execution.save()
        self.api.force_authenticate(user=self.user)
        response = self.api.patch(f"/api/v1/pas/evidences/{self.evidence.pk}/", {"descripcion": "Cambio"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_consulta_requiere_sesion_y_respeta_visibilidad_restringida(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("pas:evidence-list")).status_code, 302)
        self.plan.visibilidad = "restringida"
        self.plan.save()
        self.assertEqual(self.api.get("/api/v1/pas/evidences/").data, [])
        self.normativo.user_permissions.add(Permission.objects.get(content_type__app_label="pas", codename="view_plan"))
        # Recargar evita el caché de permisos de la instancia de usuario.
        self.normativo = User.objects.get(pk=self.normativo.pk)
        self.api.force_authenticate(user=self.normativo)
        response = self.api.get("/api/v1/pas/evidences/")
        self.assertEqual([e["id"] for e in response.data], [self.evidence.pk])

    def test_no_puede_trasladar_evidencia_a_ejecucion_ajena(self):
        response = self.api.patch(f"/api/v1/pas/evidences/{self.evidence.pk}/", {"ejecucion": self.other_execution.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.ejecucion_id, self.execution.pk)
        self.assertFalse(EventoEvidencia.objects.exists())

    def test_baja_compartida_y_rollback_exterior_conservan_archivo(self):
        from django.db import transaction
        from .evidence_services import eliminar_evidencia
        copia = Evidencia.objects.create(ejecucion=self.execution, archivo=self.evidence.archivo.name)
        storage, name = self.evidence.archivo.storage, self.evidence.archivo.name
        with self.captureOnCommitCallbacks(execute=True):
            eliminar_evidencia(copia, self.normativo)
        self.assertTrue(storage.exists(name))
        pk = self.evidence.pk
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    eliminar_evidencia(self.evidence, self.normativo)
                    raise RuntimeError("Revertir")
        self.assertTrue(Evidencia.objects.filter(pk=pk).exists())
        self.assertTrue(storage.exists(name))
        self.assertFalse(EventoEvidencia.objects.filter(evidencia_id=pk).exists())
