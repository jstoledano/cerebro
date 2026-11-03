from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from django.test import RequestFactory
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

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
)
from apps.pas.models import (
    Plan,
    Accion,
    Evidencia,
)
from apps.pas.views import PlanSummaryView
from apps.pas.views import PlanActivitiesView
from apps.pas.views import PlanClosureView

User = get_user_model()


class PASAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password",
        )

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

    def test_agenda_requires_authentication(self):
        response = self.client.get(
            reverse("pas:index")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_plan_list_requires_authentication(self):
        response = self.client.get(
            reverse("pas:plans")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_detail_public_access(self):
        request = self.factory.get(
            f"/pas/detalle/{self.plan.pk}/"
        )

        request.user = AnonymousUser()

        response = PASDetail.as_view()(
            request,
            pk=self.plan.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context_data["plan"],
            self.plan,
        )

    def test_add_plan_protected(self):
        response = self.client.get(
            reverse("pas:add")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_edit_plan_protected(self):
        response = self.client.get(
            reverse(
                "pas:plan-edit",
                args=[self.plan.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_summary_partial_public_access(self):
        response = self.client.get(
            reverse(
                "pas:plan-summary",
                args=[self.plan.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            "Editar plan",
        )

    def test_activities_partial_public_access(self):
        response = self.client.get(
            reverse(
                "pas:plan-activities",
                args=[self.plan.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            "Agregar actividad",
        )

        self.assertNotContains(
            response,
            "Editar",
        )

    def test_plan_siglas(self):
        plan_cnc = Plan(
            documento=1
        )

        self.assertEqual(
            plan_cnc.siglas,
            "CNC",
        )

        plan_pcm = Plan(
            documento=2
        )

        self.assertEqual(
            plan_pcm.siglas,
            "PCM",
        )

        plan_unknown = Plan(
            documento=99
        )

        self.assertEqual(
            plan_unknown.siglas,
            "N/A",
        )


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

    def test_activity_due_today_reports_due_today(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad de hoy",
            fecha_fin=date.today(),
            user=self.user,
        )

        self.assertEqual(
            action.salud_plazo,
            "Vence hoy",
        )

    def test_overdue_activity_reports_overdue(self):
        action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad vencida",
            fecha_fin=date(2026, 1, 1),
            user=self.user,
        )

        self.assertEqual(
            action.salud_plazo,
            "Vencida",
        )

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

        self.assertEqual(
            action.prioridad,
            "normal",
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

    def create_activity(
        self,
        number,
    ):
        Accion.objects.create(
            plan=self.plan,
            accion=f"Actividad {number}",
            responsable=self.user,
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

    def get_index_query_count(self):
        request = self.factory.get(
            "/pas/plans/"
        )

        request.user = self.user

        with CaptureQueriesContext(
            connection
        ) as queries:
            response = PASIndex.as_view()(
                request
            )

            self.assertEqual(
                response.status_code,
                200,
            )

        return len(queries)

    def test_index_queries_do_not_grow_with_number_of_activities(self):
        self.create_activity(1)

        queries_with_one_activity = self.get_index_query_count()

        for number in range(
            2,
            11,
        ):
            self.create_activity(number)

        queries_with_ten_activities = self.get_index_query_count()

        self.assertLessEqual(
            queries_with_ten_activities,
            queries_with_one_activity,
            (
                "El número de consultas del índice "
                "creció de "
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

    def create_activity(
        self,
        number,
    ):
        Accion.objects.create(
            plan=self.plan,
            accion=f"Actividad {number}",
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
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
        self.create_activity(1)

        queries_with_one = self.get_summary_query_count()

        for number in range(2, 11):
            self.create_activity(number)

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

    def create_activity(self, number):
        Accion.objects.create(
            plan=self.plan,
            accion=f"Actividad {number}",
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
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
        self.create_activity(1)

        queries_with_one = self.get_activities_query_count()

        for number in range(2, 11):
            self.create_activity(number)

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
        self.client.force_authenticate(
            user=self.user
        )

        self.restricted_action = Accion.objects.create(
            plan=self.restricted_plan,
            accion="Actividad restringida",
            responsable=self.user,
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            user=self.user,
        )

    def test_authenticated_user_does_not_see_restricted_plan(self):
        response = self.client.get(
            "/api/v1/pas/plans/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            item["id"]
            for item in response.data
        }

        self.assertIn(
            self.public_plan.pk,
            ids,
        )

        self.assertIn(
            self.internal_plan.pk,
            ids,
        )

        self.assertNotIn(
            self.restricted_plan.pk,
            ids,
        )

    def test_restricted_plan_detail_returns_404_without_permission(self):
        response = self.client.get(
            (
                "/api/v1/pas/plans/"
                f"{self.restricted_plan.pk}/"
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_user_with_view_permission_can_see_restricted_plan(self):
        permission = Permission.objects.get(
            codename="view_plan",
            content_type__app_label="pas",
        )

        self.user.user_permissions.add(
            permission
        )

        response = self.client.get(
            (
                "/api/v1/pas/plans/"
                f"{self.restricted_plan.pk}/"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            self.restricted_plan.pk,
        )

    def test_restricted_action_is_not_exposed_without_permission(self):
        response = self.client.get(
            "/api/v1/pas/actions/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            item["id"]
            for item in response.data
        }

        self.assertNotIn(
            self.restricted_action.pk,
            ids,
        )

    def test_restricted_action_detail_returns_404_without_permission(self):
        response = self.client.get(
            (
                "/api/v1/pas/actions/"
                f"{self.restricted_action.pk}/"
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_user_with_view_permission_can_see_restricted_action(self):
        permission = Permission.objects.get(
            codename="view_plan",
            content_type__app_label="pas",
        )

        self.user.user_permissions.add(
            permission
        )

        response = self.client.get(
            (
                "/api/v1/pas/actions/"
                f"{self.restricted_action.pk}/"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            self.restricted_action.pk,
        )


from django.db import IntegrityError, transaction
from apps.pas.models import CicloActividad, Ejecucion


class EvidenciasFixtureMixin:
    def setUp(self):
        super().setUp()

        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)

        settings_override = override_settings(MEDIA_ROOT=media.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

        self.user = User.objects.create_user(username="responsable-evidencias")
        self.other = User.objects.create_user(username="otro-responsable")

        self.plan = Plan.objects.create(
            nombre="Plan de pruebas de evidencias",
            documento=1,
            visibilidad="publica",
            user=self.user,
        )

        self.action = Accion.objects.create(
            plan=self.plan,
            accion="Actividad con evidencia",
            responsable=self.user,
            formato_evidencia="pdf",
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
        )

        ciclo = CicloActividad.objects.create(
            accion=self.action,
            numero=1,
            etiqueta="Ciclo de prueba",
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
        )

        self.execution = Ejecucion.objects.create(
            ciclo=ciclo,
            ambito="JL",
            responsable=self.user,
        )

        self.other_execution = Ejecucion.objects.create(
            ciclo=ciclo,
            ambito="D01",
            responsable=self.other,
        )

        self.evidence = Evidencia.objects.create(
            ejecucion=self.execution,
            descripcion="Evidencia inicial",
            archivo=self.archivo(),
            fecha=date.today(),
            user=self.user,
        )

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    @staticmethod
    def archivo(nombre="evidencia.pdf"):
        return SimpleUploadedFile(
            nombre,
            b"%PDF-1.4\n% Archivo de prueba\n%%EOF\n",
            content_type="application/pdf",
        )

    def datos(self, **cambios):
        datos = {
            "descripcion": "Evidencia nueva",
            "fecha": date.today().isoformat(),
            "archivo": self.archivo(),
        }
        datos.update(cambios)
        return datos

    def restringir_plan(self):
        self.plan.visibilidad = "restringida"
        self.plan.save(update_fields=["visibilidad"])

    def dar_permiso_consulta(self):
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="pas",
                codename="view_plan",
            )
        )


class PASEvidenciaTests(EvidenciasFixtureMixin, TestCase):
    def test_api_crea_varias_evidencias_en_la_misma_ejecucion(self):
        for descripcion in ("Segunda evidencia", "Tercera evidencia"):
            response = self.api.post(
                "/api/v1/pas/evidences/",
                self.datos(
                    ejecucion=self.execution.pk,
                    descripcion=descripcion,
                ),
                format="multipart",
            )
            self.assertEqual(response.status_code, 201, response.data)

        self.assertEqual(self.execution.evidencias.count(), 3)
        self.assertFalse(
            self.execution.evidencias.exclude(accion__isnull=True).exists()
        )

    def test_api_edita_metadatos_y_conserva_archivo(self):
        archivo_original = self.evidence.archivo.name

        response = self.api.patch(
            f"/api/v1/pas/evidences/{self.evidence.pk}/",
            {"descripcion": "Descripción actualizada"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.descripcion, "Descripción actualizada")
        self.assertEqual(self.evidence.archivo.name, archivo_original)
        self.assertEqual(self.evidence.ejecucion_id, self.execution.pk)

    def test_api_elimina_evidencia_sin_eliminar_ejecucion(self):
        response = self.api.delete(
            f"/api/v1/pas/evidences/{self.evidence.pk}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Evidencia.objects.filter(pk=self.evidence.pk).exists()
        )
        self.assertTrue(
            Ejecucion.objects.filter(pk=self.execution.pk).exists()
        )

    def test_api_rechaza_mutaciones_ajenas_aun_con_permisos_globales(self):
        self.other.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="pas",
                codename__in=[
                    "add_evidencia",
                    "change_evidencia",
                    "delete_evidencia",
                ],
            )
        )
        self.api.force_authenticate(user=self.other)

        responses = [
            self.api.post(
                "/api/v1/pas/evidences/",
                self.datos(ejecucion=self.execution.pk),
                format="multipart",
            ),
            self.api.patch(
                f"/api/v1/pas/evidences/{self.evidence.pk}/",
                {"descripcion": "Cambio ajeno"},
                format="json",
            ),
            self.api.delete(
                f"/api/v1/pas/evidences/{self.evidence.pk}/"
            ),
        ]

        for response in responses:
            self.assertEqual(response.status_code, 403, response.data)

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.descripcion, "Evidencia inicial")
        self.assertEqual(self.execution.evidencias.count(), 1)

    def test_api_bloquea_mutaciones_con_ejecucion_o_plan_cerrado(self):
        for bloqueo in ("ejecucion", "plan"):
            with self.subTest(bloqueo=bloqueo):
                self.execution.completada = bloqueo == "ejecucion"
                self.execution.save(update_fields=["completada"])

                self.plan.eliminacion = bloqueo == "plan"
                self.plan.save(update_fields=["eliminacion"])

                responses = [
                    self.api.post(
                        "/api/v1/pas/evidences/",
                        self.datos(ejecucion=self.execution.pk),
                        format="multipart",
                    ),
                    self.api.patch(
                        f"/api/v1/pas/evidences/{self.evidence.pk}/",
                        {"descripcion": "Cambio bloqueado"},
                        format="json",
                    ),
                    self.api.delete(
                        f"/api/v1/pas/evidences/{self.evidence.pk}/"
                    ),
                ]

                for response in responses:
                    self.assertEqual(response.status_code, 400, response.data)

                self.evidence.refresh_from_db()
                self.assertEqual(
                    self.evidence.descripcion,
                    "Evidencia inicial",
                )
                self.assertEqual(self.execution.evidencias.count(), 1)

    def test_api_rechaza_cambio_de_ejecucion_y_formato_incorrecto(self):
        response = self.api.patch(
            f"/api/v1/pas/evidences/{self.evidence.pk}/",
            {"ejecucion": self.other_execution.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("ejecucion", response.data)

        for nombre in ("evidencia.exe", "evidencia.docx"):
            with self.subTest(nombre=nombre):
                response = self.api.post(
                    "/api/v1/pas/evidences/",
                    self.datos(
                        ejecucion=self.execution.pk,
                        archivo=self.archivo(nombre),
                    ),
                    format="multipart",
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("archivo", response.data)

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.ejecucion_id, self.execution.pk)
        self.assertEqual(self.execution.evidencias.count(), 1)

    def test_evidence_from_restricted_plan_is_not_visible_without_permission(self):
        self.restringir_plan()

        response = self.api.get(
            f"/api/v1/pas/evidences/{self.evidence.pk}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_user_with_view_permission_can_see_restricted_evidence(self):
        self.restringir_plan()
        self.dar_permiso_consulta()

        response = self.api.get(
            f"/api/v1/pas/evidences/{self.evidence.pk}/"
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], self.evidence.pk)

    def test_base_de_datos_exige_ejecucion(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Evidencia.objects.create(
                    descripcion="Evidencia sin ejecución"
                )


class PASEvidenceDownloadTests(EvidenciasFixtureMixin, TestCase):
    def descargar(self, evidencia):
        response = self.client.get(
            reverse("pas:evidence-download", args=[evidencia.pk])
        )
        self.addCleanup(response.close)
        return response

    def test_public_evidence_file_can_be_downloaded_anonymously(self):
        response = self.descargar(self.evidence)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"%PDF-1.4",
            b"".join(response.streaming_content),
        )

    def test_internal_evidence_file_is_not_visible_anonymously(self):
        self.plan.visibilidad = "interna"
        self.plan.save(update_fields=["visibilidad"])

        response = self.descargar(self.evidence)

        self.assertEqual(response.status_code, 404)

    def test_restricted_evidence_file_is_not_visible_without_permission(self):
        self.restringir_plan()
        self.client.force_login(self.user)

        response = self.descargar(self.evidence)

        self.assertEqual(response.status_code, 404)

    def test_user_with_view_plan_permission_can_download_restricted_evidence(self):
        self.restringir_plan()
        self.dar_permiso_consulta()
        self.client.force_login(self.user)

        response = self.descargar(self.evidence)

        self.assertEqual(response.status_code, 200)

    def test_evidence_without_file_returns_404(self):
        evidencia = Evidencia.objects.create(
            ejecucion=self.execution,
            descripcion="Registro sin archivo",
        )

        response = self.descargar(evidencia)

        self.assertEqual(response.status_code, 404)


class PASEvidenceWebCRUDTests(EvidenciasFixtureMixin, TestCase):
    def test_responsable_completa_crud_sin_permisos_globales(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("pas:execution-evidence-add", args=[self.execution.pk]),
            self.datos(descripcion="Segunda evidencia"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 204)
        self.assertIn("pas:refresh-activity", response["HX-Trigger"])
        self.assertEqual(self.execution.evidencias.count(), 2)

        nueva = self.execution.evidencias.get(
            descripcion="Segunda evidencia"
        )
        archivo_original = nueva.archivo.name

        response = self.client.get(
            reverse("pas:evidence-edit", args=[nueva.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar evidencia")

        response = self.client.post(
            reverse("pas:evidence-edit", args=[nueva.pk]),
            {
                "descripcion": "Evidencia corregida",
                "fecha": date.today().isoformat(),
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 204)

        nueva.refresh_from_db()
        self.assertEqual(nueva.descripcion, "Evidencia corregida")
        self.assertEqual(nueva.archivo.name, archivo_original)

        response = self.client.get(
            reverse("pas:evidence-delete", args=[nueva.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar eliminación")
        self.assertTrue(Evidencia.objects.filter(pk=nueva.pk).exists())

        response = self.client.post(
            reverse("pas:evidence-delete", args=[nueva.pk]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Evidencia.objects.filter(pk=nueva.pk).exists())
        self.assertEqual(self.execution.evidencias.count(), 1)

    def test_consulta_incluye_solo_evidencias_de_la_ejecucion(self):
        segunda = Evidencia.objects.create(
            ejecucion=self.execution,
            descripcion="Segunda del mismo ámbito",
        )
        ajena = Evidencia.objects.create(
            ejecucion=self.other_execution,
            descripcion="Evidencia de otro ámbito",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("pas:execution-evidence", args=[self.execution.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item.pk for item in response.context["evidences"]},
            {self.evidence.pk, segunda.pk},
        )
        self.assertNotContains(response, ajena.descripcion)
        self.assertTrue(response.context["can_add_evidence"])
        self.assertTrue(response.context["can_edit_evidence"])
        self.assertTrue(response.context["can_delete_evidence"])

    def test_web_rechaza_mutaciones_de_otro_responsable(self):
        self.client.force_login(self.other)

        responses = [
            self.client.post(
                reverse(
                    "pas:execution-evidence-add",
                    args=[self.execution.pk],
                ),
                self.datos(),
            ),
            self.client.post(
                reverse("pas:evidence-edit", args=[self.evidence.pk]),
                {
                    "descripcion": "Cambio ajeno",
                    "fecha": date.today().isoformat(),
                },
            ),
            self.client.post(
                reverse("pas:evidence-delete", args=[self.evidence.pk]),
            ),
        ]

        for response in responses:
            self.assertEqual(response.status_code, 403)

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.descripcion, "Evidencia inicial")
        self.assertEqual(self.execution.evidencias.count(), 1)

    def test_web_bloquea_mutaciones_con_ejecucion_o_plan_cerrado(self):
        self.client.force_login(self.user)

        for bloqueo in ("ejecucion", "plan"):
            with self.subTest(bloqueo=bloqueo):
                self.execution.completada = bloqueo == "ejecucion"
                self.execution.save(update_fields=["completada"])

                self.plan.eliminacion = bloqueo == "plan"
                self.plan.save(update_fields=["eliminacion"])

                responses = [
                    self.client.post(
                        reverse(
                            "pas:execution-evidence-add",
                            args=[self.execution.pk],
                        ),
                        self.datos(),
                    ),
                    self.client.post(
                        reverse(
                            "pas:evidence-edit",
                            args=[self.evidence.pk],
                        ),
                        {
                            "descripcion": "Cambio bloqueado",
                            "fecha": date.today().isoformat(),
                        },
                    ),
                    self.client.post(
                        reverse(
                            "pas:evidence-delete",
                            args=[self.evidence.pk],
                        ),
                    ),
                ]

                for response in responses:
                    self.assertEqual(response.status_code, 409)

                self.evidence.refresh_from_db()
                self.assertEqual(
                    self.evidence.descripcion,
                    "Evidencia inicial",
                )
                self.assertEqual(self.execution.evidencias.count(), 1)

    def test_web_devuelve_errores_de_formato_en_formulario_htmx(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("pas:execution-evidence-add", args=[self.execution.pk]),
            self.datos(archivo=self.archivo("evidencia.docx")),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("archivo", response.context["form"].errors)
        self.assertEqual(self.execution.evidencias.count(), 1)
