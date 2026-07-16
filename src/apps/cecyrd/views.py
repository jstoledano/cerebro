from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import timedelta
from apps.cecyrd.models import Tramite
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views import View
from django.core.cache import cache
from apps.cecyrd.etl import iniciar_etl_thread


class IndexCecyrd(TemplateView):
    template_name = "cecyrd/index.html"


class CargaETLView(TemplateView):
    template_name = "cecyrd/carga.html"


class IniciarETLView(View):
    def post(self, request, *args, **kwargs):
        data_file = request.FILES.get("data_file")
        key_file = request.FILES.get("key_file")

        if not data_file:
            return JsonResponse(
                {"error": "Debes proporcionar un archivo de datos."}, status=400
            )

        is_zip = data_file.name.lower().endswith(".zip")

        # Mandar al Thread
        task_id = iniciar_etl_thread(data_file, is_zip, key_file)

        return JsonResponse({"task_id": task_id})


class ProgresoETLView(View):
    def get(self, request, task_id, *args, **kwargs):
        data = cache.get(
            task_id, {"status": "iniciando", "progress": 0, "logs": [], "stats": {}}
        )
        return JsonResponse(data)


class DashboardDataView(LoginRequiredMixin, View):
    """API que alimenta las gráficas del SGC a la velocidad de la luz."""

    def get(self, request, *args, **kwargs):
        # 1. Recibir filtros si el usuario usa la pestaña "Personalizada"
        start_date = request.GET.get("start")
        end_date = request.GET.get("end")

        # Ignoramos trámites que aún no tienen fecha de disponibilidad calculada
        queryset = Tramite.objects.exclude(tramo_disponible__isnull=True)

        if start_date:
            queryset = queryset.filter(fecha_tramite__gte=start_date)
        if end_date:
            queryset = queryset.filter(fecha_tramite__lte=end_date)

        # 2. La Magia de PostgreSQL: Agrupar por mes y calcular agregaciones
        stats = (
            queryset.annotate(month=TruncMonth("fecha_tramite"))
            .values("month")
            .annotate(
                total=Count("folio"),
                promedio=Avg("tramo_disponible"),
                # La meta de oro del SGC: 5 días
                dentro_meta=Count(
                    "folio", filter=Q(tramo_disponible__lte=timedelta(days=5))
                ),
                # Casos críticos (Fugas): Más de 10 días
                fuera_meta=Count(
                    "folio", filter=Q(tramo_disponible__gt=timedelta(days=10))
                ),
            )
            .order_by("month")
        )

        # 3. Formatear para que Chart.js lo entienda sin esfuerzo
        labels = []
        totales = []
        promedios = []
        cumplimiento = []

        # Acumuladores para las Tarjetas (KPIs globales) superiores
        global_total = 0
        global_dentro = 0
        global_fuera = 0

        for item in stats:
            if not item["month"]:
                continue

            # Formato "Ene-2026"
            mes_str = item["month"].strftime("%b %Y").capitalize()
            total = item["total"]
            dentro = item["dentro_meta"]

            global_total += total
            global_dentro += dentro
            global_fuera += item["fuera_meta"]

            # Convertir el campo Duration de Postgres a días flotantes
            promedio_dias = (
                item["promedio"].total_seconds() / 86400 if item["promedio"] else 0
            )
            pct_cumplimiento = (dentro / total * 100) if total > 0 else 0

            labels.append(mes_str)
            totales.append(total)
            promedios.append(round(promedio_dias, 2))
            cumplimiento.append(round(pct_cumplimiento, 1))

        # Calcular el cumplimiento global del periodo solicitado
        global_pct = (
            round((global_dentro / global_total * 100), 1) if global_total > 0 else 0
        )

        # 4. Devolver todo empaquetado en JSON
        return JsonResponse(
            {
                "labels": labels,
                "datasets": {
                    "totales": totales,
                    "promedios": promedios,
                    "cumplimiento": cumplimiento,
                },
                "kpis": {
                    "total_tramites": global_total,
                    "porcentaje_global": global_pct,
                    "fugas": global_fuera,
                },
            }
        )
