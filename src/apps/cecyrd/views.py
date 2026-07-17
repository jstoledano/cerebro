from django.db.models import Count, Avg, Q, Case, When, Value, F, DurationField
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import timedelta, datetime
from apps.cecyrd.models import Tramite

# === CONFIGURACIÓN DEL SGC ===
SLA_ORDINARIO = 9

PERIODOS_EXTRAORDINARIOS = [
    {
        "inicio": "2026-05-01",
        "fin": "2026-08-31",
        "dias": 30,
        "motivo": "Cambio de impresor nacional"
    },

]


class IndexCecyrd(TemplateView):
    template_name = "cecyrd/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Mandamos la meta al contexto para usarla en el HTML con {{ sla_ordinario }}
        context["sla_ordinario"] = SLA_ORDINARIO
        return context

class DashboardDataView(LoginRequiredMixin, View):
    """API que agrupa millones de registros evaluando SLAs dinámicos a prueba de balas."""

    def get(self, request, *args, **kwargs):
        start_date = request.GET.get("start")
        end_date = request.GET.get("end")

        queryset = Tramite.objects.exclude(tramo_disponible__isnull=True)

        if start_date:
            queryset = queryset.filter(fecha_tramite__gte=start_date)
        if end_date:
            queryset = queryset.filter(fecha_tramite__lte=end_date)

        # 1. Reglas del SLA dinámico para la Base de Datos (PostgreSQL)
        whens = []
        for p in PERIODOS_EXTRAORDINARIOS:
            whens.append(
                When(
                    fecha_tramite__gte=p["inicio"],
                    fecha_tramite__lte=p["fin"],
                    then=Value(timedelta(days=p["dias"])),
                )
            )

        meta_dinamica = Case(
            *whens,
            default=Value(timedelta(days=SLA_ORDINARIO)),
            output_field=DurationField(),
        )

        # 2. Agregación a nivel Base de Datos
        stats = (
            queryset.annotate(
                meta_aplicable=meta_dinamica, month=TruncMonth("fecha_tramite")
            )
            .values("month")
            .annotate(
                total=Count("folio"),
                promedio=Avg("tramo_disponible"),
                dentro_meta=Count(
                    "folio", filter=Q(tramo_disponible__lte=F("meta_aplicable"))
                ),
                fuera_meta=Count(
                    "folio", filter=Q(tramo_disponible__gt=F("meta_aplicable"))
                ),
            )
            .order_by("month")
        )

        MESES_ESPANOL = {
            "Jan": "Ene",
            "Feb": "Feb",
            "Mar": "Mar",
            "Apr": "Abr",
            "May": "May",
            "Jun": "Jun",
            "Jul": "Jul",
            "Aug": "Ago",
            "Sep": "Sep",
            "Oct": "Oct",
            "Nov": "Nov",
            "Dec": "Dic",
        }

        labels, totales, promedios, cumplimiento, metas, motivos = (
            [],
            [],
            [],
            [],
            [],
            [],
        )
        global_total, global_dentro, global_fuera = 0, 0, 0

        for item in stats:
            if not item["month"]:
                continue
            raw_month = item["month"]

            # EXTRACCIÓN SEGURA DE FECHA: Normalizamos a formato Date puro
            if isinstance(raw_month, str):
                mes_dt = datetime.strptime(raw_month[:10], "%Y-%m-%d").date()
            elif hasattr(raw_month, "date"):
                mes_dt = raw_month.date()
            else:
                mes_dt = raw_month

            # Traducción al español
            mes_en = mes_dt.strftime("%b %Y")
            partes = mes_en.split(" ")
            mes_es = f"{MESES_ESPANOL.get(partes[0], partes[0])} {partes[1]}"

            total = item["total"]
            dentro = item["dentro_meta"]

            global_total += total
            global_dentro += dentro
            global_fuera += item["fuera_meta"]

            promedio_dias = (
                item["promedio"].total_seconds() / 86400 if item["promedio"] else 0
            )
            pct_cumplimiento = (dentro / total * 100) if total > 0 else 0

            # =========================================================
            # EVALUACIÓN DE CRISIS: ¿El mes cae en periodo extraordinario?
            # =========================================================
            meta_mes = SLA_ORDINARIO
            motivo_mes = "Ordinario"

            for p in PERIODOS_EXTRAORDINARIOS:
                inicio_dt = datetime.strptime(p["inicio"], "%Y-%m-%d").date()
                fin_dt = datetime.strptime(p["fin"], "%Y-%m-%d").date()

                # AGREGA ESTO PARA VER QUÉ ESTÁ PASANDO EN LA TERMINAL
                print(
                    f"DEBUG: Comparando mes={mes_dt} vs periodo={inicio_dt} a {fin_dt}"
                )

                if inicio_dt <= mes_dt <= fin_dt:
                    print(f"DEBUG: ¡MATCH! Meta para {mes_es} es {p['dias']}")
                    meta_mes = p["dias"]
                    motivo_mes = p["motivo"]
                    break

            # Llenamos los arreglos para Chart.js
            labels.append(mes_es)
            totales.append(total)
            promedios.append(round(promedio_dias, 2))
            cumplimiento.append(round(pct_cumplimiento, 1))
            metas.append(meta_mes)  # <--- ESTO ES LO QUE LE FALTABA AL JAVASCRIPT
            motivos.append(motivo_mes)  # <--- EL MOTIVO PARA EL TOOLTIP

        global_pct = (
            round((global_dentro / global_total * 100), 1) if global_total > 0 else 0
        )

        # IMPORTANTE: Aseguramos que 'metas' y 'motivos' vayan en la respuesta JSON
        return JsonResponse(
            {
                "labels": labels,
                "datasets": {
                    "totales": totales,
                    "promedios": promedios,
                    "cumplimiento": cumplimiento,
                    "metas": metas,
                    "motivos": motivos,
                },
                "kpis": {
                    "total_tramites": global_total,
                    "porcentaje_global": global_pct,
                    "fugas": global_fuera,
                },
            }
        )


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
