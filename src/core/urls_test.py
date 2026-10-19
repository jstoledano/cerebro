from django.urls import include, path


urlpatterns = [
    path("pas/", include("apps.pas.urls")),
    path("profiles/", include("apps.profiles.urls")),
    path("api/v1/pas/", include("apps.pas.api.urls")),
]
