from django.urls import include, path

from core.views import Index


urlpatterns = [
    path("pas/", include("apps.pas.urls")),
    path("profiles/", include("apps.profiles.urls")),
    path("api/v1/pas/", include("apps.pas.api.urls")),
    path("", Index.as_view(), name="index"),
]
