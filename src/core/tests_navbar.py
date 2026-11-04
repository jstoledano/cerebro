"""Pruebas específicas de navbar y sesión (issue #139).

Las rutas auxiliares resuelven enlaces de la navbar sin cargar otros módulos.
LoginView y LogoutView corresponden a las vistas utilizadas en core.urls.
"""

from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.sessions.models import Session
from django.core.cache import caches
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.test import Client, SimpleTestCase, TestCase
from django.urls import include, path
from django.utils import timezone

from core.templatetags.navbar_tags import navbar_identity


def navbar_page(request):
    return TemplateResponse(request, "cerebro/partials/_navbar.html")


def link_target(request):
    return HttpResponse("Enlace fuera del alcance de estas pruebas.")


def auxiliary_routes(namespace, names):
    return path(
        f"{namespace}/",
        include(([path(f"{name}/", link_target, name=name) for name in names], namespace)),
    )


urlpatterns = [
    path("", navbar_page, name="index"),
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(template_name="logout.html"), name="logout"),
    auxiliary_routes("docs", ["index", "buscador", "cmi_movil_help"]),
    auxiliary_routes("pas", ["index"]),
    auxiliary_routes("cecyrd", ["index"]),
    auxiliary_routes("art141", ["dashboard"]),
    auxiliary_routes("pmml", ["register"]),
    auxiliary_routes("ideas", ["index"]),
    auxiliary_routes("pusinex", ["index", "administration", "vnm2026_cobertura", "vnm2026_actualizacion"]),
]


class AnonymousIdentityTests(SimpleTestCase):
    def test_anonymous_identity_is_empty(self):
        self.assertEqual(navbar_identity(AnonymousUser()), {})


class NavbarSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="javier", password="test-password", first_name="Javier", last_name="Sanchez"
        )
        cls.user.profile.siglas = "JST"
        cls.user.profile.save()

    def setUp(self):
        for alias in ("default", "pages"):
            caches[alias].clear()

    def test_anonymous_has_login_without_identity_or_logout(self):
        response = self.client.get("/")
        self.assertContains(response, 'href="/login/"', count=2)
        self.assertNotContains(response, "Javier Sanchez")
        self.assertNotContains(response, 'class="cmi-avatar"')
        self.assertNotContains(response, 'action="/logout/"')
        self.assertNotContains(response, "Sesión activa")

    def test_authenticated_identity_in_desktop_and_mobile(self):
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertContains(response, "JST", count=2)
        self.assertContains(response, 'title="Javier Sanchez"', count=2)
        self.assertContains(response, 'action="/logout/"', count=2)
        self.assertContains(response, 'name="csrfmiddlewaretoken"', count=2)
        self.assertNotContains(response, 'href="/login/"')
        self.assertContains(response, 'aria-controls="cmi-profile-menu"')
        self.assertContains(response, 'aria-controls="cmi-mobile-menu"')

    def test_initials_fallback(self):
        self.user.profile.siglas = None
        self.user.profile.save()
        self.assertEqual(navbar_identity(self.user), {"name": "Javier Sanchez", "initials": "JS"})

    def test_username_fallback_for_blank_name(self):
        self.user.first_name = " "
        self.user.last_name = ""
        self.user.profile.siglas = None
        self.user.save()
        self.assertEqual(navbar_identity(self.user), {"name": "javier", "initials": "J"})

    def test_missing_profile_is_supported(self):
        self.client.force_login(self.user)
        self.user.profile.delete()
        user = get_user_model().objects.get(pk=self.user.pk)
        self.assertEqual(navbar_identity(user)["initials"], "JS")
        self.assertContains(self.client.get("/"), 'title="Javier Sanchez"')

    def test_long_name_keeps_complete_accessible_text(self):
        self.user.first_name = "María" * 30
        self.user.last_name = "Sanchez" * 20
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertContains(response, f'title="{self.user.get_full_name()}"', count=2)
        self.assertContains(response, 'class="cmi-profile-full-name"')
        self.assertContains(response, "css/navbar-profile.css")
        # El desbordamiento real se verifica en navegador, no mediante HTML.

    def test_identity_is_html_escaped(self):
        self.user.first_name = '<script>alert("x")</script>'
        self.user.profile.siglas = "<b>"
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, "&lt;B&gt;")

    def test_real_login_changes_navbar(self):
        response = self.client.post("/login/", {"username": "javier", "password": "test-password"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertContains(self.client.get("/"), 'title="Javier Sanchez"')

    def test_logout_destroys_session_and_redirects_home(self):
        self.client.force_login(self.user)
        old_key = self.client.session.session_key
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/")
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        self.assertNotContains(self.client.get("/"), "Javier Sanchez")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_logout_requires_valid_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get("/")
        self.assertEqual(client.post("/logout/").status_code, 403)
        self.assertIn(SESSION_KEY, client.session)
        token = client.cookies["csrftoken"].value
        self.assertRedirects(client.post("/logout/", {"csrfmiddlewaretoken": token}), "/")
        self.assertNotIn(SESSION_KEY, client.session)

    def test_expired_session_shows_anonymous_navbar(self):
        self.client.force_login(self.user)
        Session.objects.filter(session_key=self.client.session.session_key).update(expire_date=timezone.now())
        response = self.client.get("/")
        self.assertContains(response, 'href="/login/"')
        self.assertNotContains(response, "Javier Sanchez")

    def test_shared_cache_does_not_mix_identities(self):
        self.client.get("/")  # Populate the public cache first.
        other = get_user_model().objects.create_user(username="ana", first_name="Ana", last_name="López")
        second_client = Client()
        second_client.force_login(other)
        self.client.force_login(self.user)
        response = self.client.get("/")
        other_response = second_client.get("/")
        self.assertContains(response, "Javier Sanchez")
        self.assertNotContains(response, "Ana López")
        self.assertContains(other_response, "Ana López")
        self.assertNotContains(other_response, "Javier Sanchez")
        self.assertNotContains(Client().get("/"), "Javier Sanchez")
