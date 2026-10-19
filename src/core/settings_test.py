from .settings import *


EXCLUDED_TEST_APPS = {
    "django.contrib.gis",
    "apps.pusinex.config.PusinexConfig",
    "apps.art141.config.Art141Config",
}

INSTALLED_APPS = [
    app
    for app in INSTALLED_APPS
    if app not in EXCLUDED_TEST_APPS
]

ROOT_URLCONF = "core.urls_test"
