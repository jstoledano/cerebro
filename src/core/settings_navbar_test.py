"""Configuración aislada para la issue #139.

Ejecutar desde src:
python manage.py test core.tests_navbar --settings=core.settings_navbar_test
No requiere .env, Redis, GIS ni aplicaciones ajenas a navbar/sesión.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "navbar-tests-only-not-for-production"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "apps.profiles.config.ProfilesConfig",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
LANGUAGE_CODE = "es-mx"
ROOT_URLCONF = "core.tests_navbar"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index"
STATIC_URL = "/assets/"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MIDDLEWARE = [
    "core.cache_middleware.SelectiveUpdateCacheMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.cache_middleware.SelectiveFetchFromCacheMiddleware",
]
CACHES = {
    alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": alias}
    for alias in ("default", "pages")
}
CACHE_MIDDLEWARE_ALIAS = "pages"
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = "navbar-tests"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "apps" / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
        ],
        "libraries": {
            "sgc": "core.templatetags.sgc",
            "navbar_tags": "core.templatetags.navbar_tags",
        },
    },
}]
