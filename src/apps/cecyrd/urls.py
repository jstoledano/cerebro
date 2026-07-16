from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.cecyrd import views

app_name = "cecyrd"

urlpatterns = [
    # Rutas visuales
    path("", views.IndexCecyrd.as_view(), name="index"),
    path("carga/", login_required(views.CargaETLView.as_view()), name="carga"),

    # Rutas API para el proceso ETL
    path("api/etl/iniciar/", login_required(views.IniciarETLView.as_view()), name="api_etl_iniciar"),
    path("api/etl/progreso/<str:task_id>/", login_required(views.ProgresoETLView.as_view()), name="api_etl_progreso"),

    # API DEL CUADRO DE MANDO SGC
    path("api/dashboard/", views.DashboardDataView.as_view(), name="api_dashboard"),
]
