from django.urls import include, path


urlpatterns = [
    path("pas/", include("apps.pas.urls")),
    path("profiles/", include("apps.profiles.urls")),
]
