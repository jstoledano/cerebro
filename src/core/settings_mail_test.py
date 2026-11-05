"""Pruebas aisladas de notificaciones. Todos los mensajes quedan en memoria."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "only-for-mail-tests"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "core",
    "apps.profiles.config.ProfilesConfig", "apps.pas.config.PasConfig",
    "apps.pmml.config.PmmlConfig", "core.mail_test_apps.DocsMailTestConfig",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
TIME_ZONE = "America/Mexico_City"
LANGUAGE_CODE = "es-mx"
ROOT_URLCONF = "core.urls_mail_test"
LOGIN_URL = "/login/"
STATIC_URL = "/assets/"
SITE_URL = "http://testserver"
NOTIFICACIONES_MODO = "simular"
NOTIFICACIONES_CORREO_PRUEBA = "javier.sanchezt@ine.mx"
DEFAULT_FROM_EMAIL = "CMI <cmi@example.org>"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "apps" / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
