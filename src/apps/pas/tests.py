import unittest

from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from django.test import RequestFactory

from apps.pas.views import PASIndex, PASDetail
from django.http import Http404
from datetime import date
from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from apps.pas.forms import PlanForm, AccionForm
from django.core.exceptions import PermissionDenied
from apps.pas.views import PASAdd, PlanUpdateView
from apps.pas.views import (
    ActivityCreateView,
    ActivityUpdateView,
    ActivityDeleteView,
    FollowUpCreateView,
)
from apps.pas.models import Plan, Accion, Seguimiento, Evidencia
from apps.pas.views import PlanSummaryView
from apps.pas.views import PlanActivitiesView
from apps.pas.views import PlanClosureView

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
        request.user = AnonymousUser()
        response = PASIndex.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_detail_public_access(self):
        request = self.factory.get(f"/pas/detalle/{self.plan.pk}/")
        request.user = AnonymousUser()
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
            "visibilidad": "publica",
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

    def test_priority_defaults_to_normal(self):
        action = Accion.objects.create(
            plan=Plan.objects.create(
                nombre="Plan prioridad",
                documento=1,
                folio="PRIORITY-001",
                fecha_llenado=date.today(),
            ),
            accion="Actividad priorizada",
        )

        self.assertEqual(action.prioridad, "normal")


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
        request.user = AnonymousUser()

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
        request.user = AnonymousUser()
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
        request.user = AnonymousUser()
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

class PASPlanClosureTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="closureuser",
            password="password",
        )

        permission = Permission.objects.get(
            codename="change_plan",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        self.plan = Plan.objects.create(
            nombre="Plan con actividad abierta",
            documento=1,
            folio="CLOSURE-001",
            fecha_llenado=date.today(),
            user=self.user,
        )

        self.action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad abierta",
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

    def test_plan_can_be_closed_with_open_activities(self):
        request = self.factory.post(
            f"/pas/{self.plan.pk}/closure/",
            {
                "resultado": "close",
                "comentarios": (
                    "Cierre registrado para efectos de seguimiento."
                ),
            },
        )
        request.user = self.user

        response = PlanClosureView.as_view()(
            request,
            pk=self.plan.pk,
        )

        self.assertEqual(response.status_code, 302)

        self.plan.refresh_from_db()

        self.assertTrue(self.plan.eliminacion)
        self.assertFalse(self.plan.recurrencia)


class PASPlanVisibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="visibilityuser",
            password="password",
        )

        self.public_plan = Plan.objects.create(
            nombre="Plan público",
            documento=1,
            folio="VIS-001",
            fecha_llenado=date.today(),
            visibilidad="publica",
            user=self.user,
        )

        self.internal_plan = Plan.objects.create(
            nombre="Plan interno",
            documento=1,
            folio="VIS-002",
            fecha_llenado=date.today(),
            visibilidad="interna",
            user=self.user,
        )

        self.restricted_plan = Plan.objects.create(
            nombre="Plan restringido",
            documento=1,
            folio="VIS-003",
            fecha_llenado=date.today(),
            visibilidad="restringida",
            user=self.user,
        )

    def test_anonymous_user_sees_only_public_plans(self):
        from django.contrib.auth.models import AnonymousUser

        plans = Plan.objects.visible_to(AnonymousUser())

        self.assertQuerySetEqual(
            plans.order_by("pk"),
            [self.public_plan],
        )

    def test_authenticated_user_sees_public_and_internal_plans(self):
        plans = Plan.objects.visible_to(self.user)

        self.assertQuerySetEqual(
            plans.order_by("pk"),
            [
                self.public_plan,
                self.internal_plan,
            ],
        )

    def test_user_with_view_permission_sees_restricted_plans(self):
        permission = Permission.objects.get(
            codename="view_plan",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        plans = Plan.objects.visible_to(self.user)

        self.assertQuerySetEqual(
            plans.order_by("pk"),
            [
                self.public_plan,
                self.internal_plan,
                self.restricted_plan,
            ],
        )


class PASPlanVisibilityViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.owner = User.objects.create_user(
            username="visibilityowner",
            password="password",
        )

        self.public_plan = Plan.objects.create(
            nombre="Plan público",
            documento=1,
            folio="VIEW-001",
            fecha_llenado=date.today(),
            visibilidad="publica",
            user=self.owner,
        )

        self.internal_plan = Plan.objects.create(
            nombre="Plan interno",
            documento=1,
            folio="VIEW-002",
            fecha_llenado=date.today(),
            visibilidad="interna",
            user=self.owner,
        )

        self.restricted_plan = Plan.objects.create(
            nombre="Plan restringido",
            documento=1,
            folio="VIEW-003",
            fecha_llenado=date.today(),
            visibilidad="restringida",
            user=self.owner,
        )

    def test_anonymous_can_open_public_plan(self):
        request = self.factory.get(
            f"/pas/detalle/{self.public_plan.pk}/"
        )
        request.user = AnonymousUser()

        response = PASDetail.as_view()(
            request,
            pk=self.public_plan.pk,
        )

        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_open_internal_plan(self):
        request = self.factory.get(
            f"/pas/detalle/{self.internal_plan.pk}/"
        )
        request.user = AnonymousUser()

        with self.assertRaises(Http404):
            PASDetail.as_view()(
                request,
                pk=self.internal_plan.pk,
            )

    def test_authenticated_user_can_open_internal_plan(self):
        request = self.factory.get(
            f"/pas/detalle/{self.internal_plan.pk}/"
        )
        request.user = self.owner

        response = PASDetail.as_view()(
            request,
            pk=self.internal_plan.pk,
        )

        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_without_view_permission_cannot_open_restricted_plan(self):
        request = self.factory.get(
            f"/pas/detalle/{self.restricted_plan.pk}/"
        )
        request.user = self.owner

        with self.assertRaises(Http404):
            PASDetail.as_view()(
                request,
                pk=self.restricted_plan.pk,
            )

    def test_user_with_view_permission_can_open_restricted_plan(self):
        permission = Permission.objects.get(
            codename="view_plan",
            content_type__app_label="pas",
        )
        self.owner.user_permissions.add(permission)

        request = self.factory.get(
            f"/pas/detalle/{self.restricted_plan.pk}/"
        )
        request.user = self.owner

        response = PASDetail.as_view()(
            request,
            pk=self.restricted_plan.pk,
        )

        self.assertEqual(response.status_code, 200)

class PASAPIVisibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="apivisibilityuser",
            password="password",
        )

        self.public_plan = Plan.objects.create(
            nombre="Plan público API",
            documento=1,
            folio="API-VIS-001",
            fecha_llenado=date.today(),
            visibilidad="publica",
            user=self.user,
        )

        self.internal_plan = Plan.objects.create(
            nombre="Plan interno API",
            documento=1,
            folio="API-VIS-002",
            fecha_llenado=date.today(),
            visibilidad="interna",
            user=self.user,
        )

        self.restricted_plan = Plan.objects.create(
            nombre="Plan restringido API",
            documento=1,
            folio="API-VIS-003",
            fecha_llenado=date.today(),
            visibilidad="restringida",
            user=self.user,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.restricted_action = Accion.objects.create(
            plan=self.restricted_plan,
            accion="Actividad restringida",
            responsable=self.user,
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

        self.restricted_followup = Seguimiento.objects.create(
            accion=self.restricted_action,
            descripcion="Seguimiento restringido",
            fecha=date.today(),
            estado=1,
            responsable=self.user,
            user=self.user,
        )

    def test_authenticated_user_does_not_see_restricted_plan(self):
        response = self.client.get("/api/v1/pas/plans/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertIn(self.public_plan.pk, ids)
        self.assertIn(self.internal_plan.pk, ids)
        self.assertNotIn(self.restricted_plan.pk, ids)

    def test_restricted_plan_detail_returns_404_without_permission(self):
        response = self.client.get(
            f"/api/v1/pas/plans/{self.restricted_plan.pk}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_user_with_view_permission_can_see_restricted_plan(self):
        permission = Permission.objects.get(
            codename="view_plan",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        response = self.client.get(
            f"/api/v1/pas/plans/{self.restricted_plan.pk}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            self.restricted_plan.pk,
        )

    def test_restricted_action_is_not_exposed_without_permission(self):
        response = self.client.get("/api/v1/pas/actions/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(
            self.restricted_action.pk,
            ids,
        )

    def test_restricted_action_detail_returns_404_without_permission(self):
        response = self.client.get(f"/api/v1/pas/actions/{self.restricted_action.pk}/")

        self.assertEqual(response.status_code, 404)

    def test_restricted_followup_is_not_exposed_without_permission(self):
        response = self.client.get("/api/v1/pas/followups/")

        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.data}

        self.assertNotIn(
            self.restricted_followup.pk,
            ids,
        )

    def test_restricted_followup_detail_returns_404_without_permission(self):
        response = self.client.get(
            f"/api/v1/pas/followups/{self.restricted_followup.pk}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_user_with_view_permission_can_see_restricted_action_and_followup(self):
        permission = Permission.objects.get(
            codename="view_plan",
            content_type__app_label="pas",
        )
        self.user.user_permissions.add(permission)

        action_response = self.client.get(
            f"/api/v1/pas/actions/{self.restricted_action.pk}/"
        )

        followup_response = self.client.get(
            f"/api/v1/pas/followups/{self.restricted_followup.pk}/"
        )

        self.assertEqual(action_response.status_code, 200)
        self.assertEqual(followup_response.status_code, 200)


class PASEvidenciaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="evidenceuser",
            password="password",
        )

        self.plan = Plan.objects.create(
            nombre="Plan de evidencia",
            documento=1,
            folio="EVID-001",
            fecha_llenado=date.today(),
            user=self.user,
        )

        self.action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad con evidencia",
            responsable=self.user,
            fecha_fin=date.today(),
            user=self.user,
        )

    def test_activity_can_have_multiple_evidences(self):
        Evidencia.objects.create(
            accion=self.action,
            descripcion="Primera evidencia",
            user=self.user,
        )

        Evidencia.objects.create(
            accion=self.action,
            descripcion="Segunda evidencia",
            user=self.user,
        )

        self.assertEqual(
            self.action.evidencias.count(),
            2,
        )
