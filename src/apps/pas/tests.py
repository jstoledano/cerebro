import unittest

from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from django.test import RequestFactory

from apps.pas.views import PASIndex, PASDetail

from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.pas.models import Plan, Accion
from apps.pas.forms import PlanForm, AccionForm


User = get_user_model()

# @unittest.skip("Motivo por el que se omite")
class PASAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.plan = Plan.objects.create(
            folio=1,
            fecha_llenado=date.today(),
            user=self.user,
            documento=1,
            desc_cnc="Test Plan",
            analisis="Test Analysis",
        )
        self.action = Accion.objects.create(
            plan=self.plan,
            accion="Test Action",
            responsable=self.user,
            fecha_fin=date.today(),
        )
        self.factory = RequestFactory()

    def test_index_public_access(self):
        request = self.factory.get("/pas/")

        response = PASIndex.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_detail_public_access(self):
        request = self.factory.get(f"/pas/detalle/{self.plan.pk}/")

        response = PASDetail.as_view()(
            request,
            pk=self.plan.pk,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["plan"], self.plan)

    def test_add_plan_protected(self):
        """Test that adding a plan requires login."""
        response = self.client.get(reverse("pas:add"))
        self.assertNotEqual(response.status_code, 200)
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_edit_plan_protected(self):
        """Test that editing a plan requires login."""
        response = self.client.get(reverse("pas:plan-edit", args=[self.plan.pk]))
        self.assertEqual(response.status_code, 302)

    def test_summary_partial_public_access(self):
        """Test that plan summary partial is accessible."""
        response = self.client.get(reverse("pas:plan-summary", args=[self.plan.pk]))
        self.assertEqual(response.status_code, 200)
        # Ensure 'Editar plan' button is NOT present
        self.assertNotContains(response, "Editar plan")

    def test_activities_partial_public_access(self):
        """Test that activities list partial is accessible."""
        response = self.client.get(reverse("pas:plan-activities", args=[self.plan.pk]))
        self.assertEqual(response.status_code, 200)
        # Ensure 'Agregar actividad' button is NOT present
        self.assertNotContains(response, "Agregar actividad")
        # Ensure 'Editar' button is NOT present
        self.assertNotContains(response, "Editar")

    def test_plan_siglas(self):
        """Test the siglas property of Plan model."""
        plan_cnc = Plan(documento=1)  # CNC
        self.assertEqual(plan_cnc.siglas, "CNC")
        plan_pcm = Plan(documento=2)  # PCM
        self.assertEqual(plan_pcm.siglas, "PCM")
        plan_unknown = Plan(documento=99)
        self.assertEqual(plan_unknown.siglas, "N/A")


class PASPlanFormTests(TestCase):
    def base_data(self):
        return {
            "nombre": "Plan de prueba",
            "documento": 1,
            "folio": "TEST-001",
            "fecha_llenado": "2026-10-19",
        }

    def test_otra_fuente_required_when_fuente_is_otros(self):
        data = self.base_data()
        data.update(
            {
                "fuente": 9,
                "otra_fuente": "",
            }
        )

        form = PlanForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("otra_fuente", form.errors)

    def test_otra_fuente_not_required_for_revision_direccion(self):
        data = self.base_data()
        data.update(
            {
                "fuente": 4,
                "otra_fuente": "",
            }
        )

        form = PlanForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)

    def test_fecha_termino_cannot_be_before_fecha_inicio(self):
        data = self.base_data()
        data.update(
            {
                "documento": 2,
                "fecha_inicio": "2026-10-20",
                "fecha_termino": "2026-10-19",
            }
        )

        form = PlanForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("fecha_termino", form.errors)


class PASAccionFormTests(TestCase):
    def test_fecha_fin_cannot_be_before_fecha_inicio(self):
        form = AccionForm(
            data={
                "accion": "Actividad de prueba",
                "fecha_inicio": "2026-10-20",
                "fecha_fin": "2026-10-19",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("fecha_fin", form.errors)


class PASAPIPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="apiuser",
            password="password",
        )

        self.plan = Plan.objects.create(
            nombre="Plan API",
            documento=1,
            folio="API-001",
            fecha_llenado=date.today(),
            user=self.user,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_user_without_permission_cannot_create_plan(self):
        response = self.client.post(
            "/api/v1/pas/plans/",
            {
                "nombre": "Nuevo plan",
                "documento": 1,
                "folio": "API-002",
                "fecha_llenado": date.today().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_cannot_create_activity_in_closed_plan(self):
        permission = Permission.objects.get(
            codename="add_accion",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        self.plan.eliminacion = True
        self.plan.save(update_fields=["eliminacion"])

        response = self.client.post(
            "/api/v1/pas/actions/",
            {
                "plan": self.plan.pk,
                "accion": "Actividad que no debe registrarse",
                "fecha_inicio": date.today().isoformat(),
                "fecha_fin": date.today().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_cannot_create_followup_in_closed_plan(self):
        accion = Accion.objects.create(
            plan=self.plan,
            accion="Actividad API",
            responsable=self.user,
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

        permission = Permission.objects.get(
            codename="add_seguimiento",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        self.plan.eliminacion = True
        self.plan.save(update_fields=["eliminacion"])

        response = self.client.post(
            "/api/v1/pas/followups/",
            {
                "accion": accion.pk,
                "descripcion": "Seguimiento de prueba",
                "fecha": date.today().isoformat(),
                "estado": 1,
                "responsable": self.user.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_activity_rejects_invalid_date_range(self):
        permission = Permission.objects.get(
            codename="add_accion",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        response = self.client.post(
            "/api/v1/pas/actions/",
            {
                "plan": self.plan.pk,
                "accion": "Actividad con fechas inválidas",
                "fecha_inicio": "2026-10-20",
                "fecha_fin": "2026-10-19",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("fecha_fin", response.data)
