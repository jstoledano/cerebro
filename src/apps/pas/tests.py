import unittest

from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from django.test import RequestFactory

from apps.pas.views import PASIndex, PASDetail

from datetime import date
from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.pas.forms import PlanForm, AccionForm
from django.core.exceptions import PermissionDenied
from apps.pas.views import PASAdd, PlanUpdateView
from apps.pas.views import (
    ActivityCreateView,
    ActivityUpdateView,
    ActivityDeleteView,
    FollowUpCreateView,
)
from apps.pas.models import Plan, Accion, Seguimiento
from apps.pas.views import PlanSummaryView
from apps.pas.views import PlanActivitiesView

User = get_user_model()


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


class PASWebPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="webuser",
            password="password",
        )

        self.plan = Plan.objects.create(
            nombre="Plan de prueba",
            documento=1,
            folio="WEB-001",
            fecha_llenado=date.today(),
            user=self.user,
        )

    def test_authenticated_user_without_add_permission_cannot_add_plan(self):
        request = self.factory.get("/pas/add/")
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            PASAdd.as_view()(request)

    def test_user_with_add_permission_can_open_add_plan(self):
        permission = Permission.objects.get(
            codename="add_plan",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        request = self.factory.get("/pas/add/")
        request.user = self.user

        response = PASAdd.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_without_change_permission_cannot_edit_plan(self):
        request = self.factory.get(
            f"/pas/{self.plan.pk}/edit/"
        )
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            PlanUpdateView.as_view()(
                request,
                pk=self.plan.pk,
            )

    def test_user_with_change_permission_can_open_edit_plan(self):
        permission = Permission.objects.get(
            codename="change_plan",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        request = self.factory.get(
            f"/pas/{self.plan.pk}/edit/"
        )
        request.user = self.user

        response = PlanUpdateView.as_view()(
            request,
            pk=self.plan.pk,
        )

        self.assertEqual(response.status_code, 200)


class PASClosedPlanTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="closedplanuser",
            password="password",
        )

        permissions = Permission.objects.filter(
            content_type__app_label="pas",
            codename__in=[
                "add_accion",
                "change_accion",
                "delete_accion",
                "add_seguimiento",
            ],
        )
        self.user.user_permissions.add(*permissions)

        self.plan = Plan.objects.create(
            nombre="Plan cerrado",
            documento=1,
            folio="CLOSED-001",
            fecha_llenado=date.today(),
            eliminacion=True,
            user=self.user,
        )

        self.action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad existente",
            responsable=self.user,
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

    def test_cannot_add_activity_to_closed_plan(self):
        request = self.factory.get(
            f"/pas/{self.plan.pk}/activities/add/"
        )
        request.user = self.user

        response = ActivityCreateView.as_view()(
            request,
            pk=self.plan.pk,
        )

        self.assertEqual(response.status_code, 409)

    def test_cannot_edit_activity_in_closed_plan(self):
        request = self.factory.get(
            f"/pas/activities/{self.action.pk}/edit/"
        )
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            ActivityUpdateView.as_view()(
                request,
                pk=self.action.pk,
            )

    def test_cannot_delete_activity_in_closed_plan(self):
        request = self.factory.get(
            f"/pas/activities/{self.action.pk}/delete/"
        )
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            ActivityDeleteView.as_view()(
                request,
                pk=self.action.pk,
            )

    def test_cannot_add_followup_to_closed_plan(self):
        request = self.factory.get(
            f"/pas/activities/{self.action.pk}/followups/add/"
        )
        request.user = self.user

        response = FollowUpCreateView.as_view()(
            request,
            pk=self.action.pk,
        )

        self.assertEqual(response.status_code, 409)


class PASAccionStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="stateuser",
            password="password",
        )

        self.plan = Plan.objects.create(
            nombre="Plan de estados",
            documento=1,
            folio="STATE-001",
            fecha_llenado=date.today(),
            user=self.user,
        )

    def test_activity_without_followup_has_no_operational_state(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad sin seguimiento",
            fecha_fin=date.today(),
            user=self.user,
        )

        self.assertIsNone(action.estado_operativo)

    def test_activity_due_today_reports_due_today(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad de hoy",
            fecha_fin=date.today(),
            user=self.user,
        )

        self.assertEqual(action.salud_plazo, "Vence hoy")

    def test_operational_state_comes_from_latest_followup(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad con seguimiento",
            fecha_fin=date.today(),
            user=self.user,
        )

        Seguimiento.objects.create(
            accion=action,
            descripcion="Esperando respuesta",
            fecha=date.today(),
            estado=3,
            responsable=self.user,
            user=self.user,
        )

        self.assertEqual(
            action.estado_operativo,
            "En espera de una respuesta",
        )

    def test_overdue_activity_reports_overdue(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad vencida",
            fecha_fin=date(2026, 1, 1),
            user=self.user,
        )

        self.assertEqual(action.salud_plazo, "Vencida")

    def test_activity_without_due_date_reports_no_due_date(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad sin fecha",
            fecha_fin=None,
            user=self.user,
        )

        self.assertEqual(
            action.salud_plazo,
            "Sin fecha de término",
        )

    def test_closed_activity_reports_closed_in_time(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad cerrada",
            fecha_fin=date.today(),
            user=self.user,
        )

        Seguimiento.objects.create(
            accion=action,
            descripcion="Actividad registrada como cerrada",
            fecha=date.today(),
            estado=99,
            responsable=self.user,
            user=self.user,
        )

        self.assertEqual(
            action.salud_plazo,
            "Cerrada en tiempo",
        )

    def test_closed_activity_reports_closed_late(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad cerrada fuera de tiempo",
            fecha_fin=date(2026, 1, 1),
            user=self.user,
        )

        Seguimiento.objects.create(
            accion=action,
            descripcion="Cierre registrado",
            fecha=date.today(),
            estado=99,
            responsable=self.user,
            user=self.user,
        )

        self.assertEqual(
            action.salud_plazo,
            "Cerrada fuera de tiempo",
        )


class PASIndexQueryTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="queryuser",
            password="password",
        )

        self.plan = Plan.objects.create(
            nombre="Plan de consultas",
            documento=1,
            folio="QUERY-001",
            fecha_llenado=date.today(),
            user=self.user,
        )

    def create_activity_with_followup(self, number):
        action = Accion.objects.create(
            plan=self.plan,
            accion=f"Actividad {number}",
            responsable=self.user,
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

        Seguimiento.objects.create(
            accion=action,
            descripcion=f"Seguimiento {number}",
            fecha=date.today(),
            estado=1,
            responsable=self.user,
            user=self.user,
        )

    def get_index_query_count(self):
        request = self.factory.get("/pas/")

        with CaptureQueriesContext(connection) as queries:
            response = PASIndex.as_view()(request)

            self.assertEqual(response.status_code, 200)

        return len(queries)

    def test_index_queries_do_not_grow_with_number_of_activities(self):
        self.create_activity_with_followup(1)

        queries_with_one_activity = self.get_index_query_count()

        for number in range(2, 11):
            self.create_activity_with_followup(number)

        queries_with_ten_activities = self.get_index_query_count()

        self.assertEqual(
            queries_with_ten_activities,
            queries_with_one_activity,
            (
                "El número de consultas del índice creció de "
                f"{queries_with_one_activity} a "
                f"{queries_with_ten_activities}."
            ),
        )


class PASPlanSummaryQueryTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="summaryqueryuser",
            password="password",
        )

        self.plan = Plan.objects.create(
            nombre="Plan resumen",
            documento=1,
            folio="SUMMARY-001",
            fecha_llenado=date.today(),
            user=self.user,
        )

    def create_activity_with_followup(self, number):
        action = Accion.objects.create(
            plan=self.plan,
            accion=f"Actividad {number}",
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

        Seguimiento.objects.create(
            accion=action,
            descripcion=f"Seguimiento {number}",
            fecha=date.today(),
            estado=1,
            user=self.user,
        )

    def get_summary_query_count(self):
        request = self.factory.get(
            f"/pas/{self.plan.pk}/summary/"
        )

        with CaptureQueriesContext(connection) as queries:
            response = PlanSummaryView.as_view()(
                request,
                pk=self.plan.pk,
            )

            self.assertEqual(response.status_code, 200)

        return len(queries)

    def test_summary_queries_do_not_grow_with_number_of_activities(self):
        self.create_activity_with_followup(1)

        queries_with_one = self.get_summary_query_count()

        for number in range(2, 11):
            self.create_activity_with_followup(number)

        queries_with_ten = self.get_summary_query_count()

        self.assertEqual(
            queries_with_ten,
            queries_with_one,
        )


class PASPlanActivitiesQueryTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="activitiesqueryuser",
            password="password",
        )

        self.plan = Plan.objects.create(
            nombre="Plan actividades",
            documento=1,
            folio="ACTIVITIES-001",
            fecha_llenado=date.today(),
            user=self.user,
        )

    def create_activity_with_followups(self, number):
        action = Accion.objects.create(
            plan=self.plan,
            accion=f"Actividad {number}",
            responsable=self.user,
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

        Seguimiento.objects.create(
            accion=action,
            descripcion=f"Primer seguimiento {number}",
            fecha=date.today(),
            estado=1,
            responsable=self.user,
            user=self.user,
        )

        Seguimiento.objects.create(
            accion=action,
            descripcion=f"Segundo seguimiento {number}",
            fecha=date.today(),
            estado=3,
            responsable=self.user,
            user=self.user,
        )

    def get_activities_query_count(self):
        request = self.factory.get(
            f"/pas/{self.plan.pk}/activities/"
        )

        with CaptureQueriesContext(connection) as queries:
            response = PlanActivitiesView.as_view()(
                request,
                pk=self.plan.pk,
            )

            self.assertEqual(response.status_code, 200)

        return len(queries)

    def test_activity_queries_do_not_grow_with_number_of_activities(self):
        self.create_activity_with_followups(1)

        queries_with_one = self.get_activities_query_count()

        for number in range(2, 11):
            self.create_activity_with_followups(number)

        queries_with_ten = self.get_activities_query_count()

        self.assertEqual(
            queries_with_ten,
            queries_with_one,
            (
                "El número de consultas de actividades creció de "
                f"{queries_with_one} a {queries_with_ten}."
            ),
        )
