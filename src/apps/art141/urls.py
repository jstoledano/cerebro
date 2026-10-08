from django.urls import path

from apps.art141.views import (
    DashboardArt141,
    DashboardVA,
)

app_name = "art141"

urlpatterns = [
    path(
        "",
        DashboardArt141.as_view(),
        name="dashboard",
    ),
    path(
        "va/",
        DashboardVA.as_view(),
        name="va",
    ),
]
