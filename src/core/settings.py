"""Configuración del proyecto cerebro."""

import sys
from unipath import Path
import environ
from django.contrib.messages import constants as messages

VERSION = '2.0.0'

BASE_DIR = Path(__file__).ancestor(2)
APPS_DIR = BASE_DIR.child('apps')
env = environ.Env(DEBUG=(bool, False),)
environ.Env.read_env(BASE_DIR.child('.env'))

SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = [
    'https://sgctlaxcala.com.mx',
    'https://www.sgctlaxcala.com.mx'
]
CORS_ORIGIN_WHITELIST = [
    'https://sgctlaxcala.com.mx',
    'https://www.sgctlaxcala.com.mx'
]

if env('SSL', default=False) is True:
    SECURE_SSL_REDIRECT = False

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize'
]
THIRD_PARTY_APPS = [
    'crispy_forms',
    "crispy_bootstrap5",
    'django_extensions',
    'watson',
    'simple_history',
    'guardian',
    'tinymce',
    'captcha',
    'anymail',
    "compressor",
]
LOCAL_APPS = [
    'core',
    'apps.profiles.config.ProfilesConfig',
    'apps.docs.config.DocsConfig',
    'apps.ideas.config.IdeasConfig',
    'apps.carto.config.CartoConfig',
    'apps.pas.config.PasConfig',
    'apps.kpi.apps.KpiConfig',
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            APPS_DIR.child('templates'),
            'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.docs.views.reportes_context'
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': env.db()
}

if 'test' in sys.argv or 'test_coverage' in sys.argv:
    DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'

if DEBUG:
    DJANGO_ALLOW_ASYNC_UNSAFE = env("DJANGO_ALLOW_ASYNC_UNSAFE", default=True)
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        }
    ]
    SITE_URL = "http://127.0.0.1:8000"
else:
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ]


LANGUAGE_CODE = env('LOCALE', default='es-mx')
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_L10N = True
USE_TZ = True
SITE_ID = 1

LOGIN_REDIRECT_URL = 'index'
LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = 'index'

STATIC_URL = 'assets/'
STATICFILES_DIRS = [
    APPS_DIR.child('static'),
]

MEDIA_ROOT = APPS_DIR.child('media')
MEDIA_URL = '/media/'
FILE_UPLOAD_PERMISSIONS = 0o644

CRISPY_TEMPLATE_PACK = 'bootstrap5'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

LOGGING = {
    'disable_existing_loggers': False,
    'version': 1,
    'handlers': {
        'console': {
            # logging handler that outputs log messages to terminal
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',  # message level to be written to console
        },
    },
    'loggers': {
        '': {
            # this sets root level logger to log debug and higher level
            # logs to console. All other loggers inherit settings from
            # root level logger.
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,    # this tells logger to send logging message
                                   # to its parent (will send if set to True)
        },
        # 'django.db': {
        #     # django also has database level logging
        #     'level': 'DEBUG'
        # },
    },
}

INTERNAL_IPS = '127.0.0.1'

NOTEBOOK_ARGUMENTS = [
    # exposes IP and port
    '--ip=localhost',
    '--port=8888',
    # disables the browser
    '--no-browser',
]

# CMI-1 Configuración de Guardian
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
    'guardian.backends.ObjectPermissionBackend',
)

# Caso no. 35, Backend para correo
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=True)
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')

ANYMAIL = {
    "MAILGUN_API_KEY": env('EMAIL_HOST_USER'),
    "MAILGUN_SENDER_DOMAIN": env('EMAIL_HOST_PASSWORD')
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

TINYMCE_DEFAULT_CONFIG = {
    "height": 300,
}

X_FRAME_OPTIONS = "SAMEORIGIN"
RECAPTCHA_PUBLIC_KEY = env('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = env('RECAPTCHA_PRIVATE_KEY')

COMPRESS_ROOT = APPS_DIR.child('static')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)
