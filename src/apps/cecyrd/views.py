import calendar
import json
from datetime import datetime, timedelta
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Avg, Case, Count, DurationField, F, Q, Value, When
from django.db.models.functions import TruncMonth, ExtractDay, TruncWeek
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.core.cache import cache
from .etl import iniciar_etl_thread
from django.http import HttpResponse
from django.views import View
from weasyprint import HTML

from .models import Tramite, RevisionDireccion

# === CONFIGURACIÓN DEL SGC ===
SLA_ORDINARIO = 9

PERIODOS_EXTRAORDINARIOS = [
    {
        "inicio": "2026-05-22",
        "fin": "2026-06-10",
        "dias": 22,
        "motivo": "correo electrónico 220526-01",
    },
    {
        "inicio": "2026-06-11",
        "fin": "2026-12-31",
        "dias": 20,
        "motivo": "correo electrónico 100626-01",
    },
]


class IndexCecyrd(TemplateView):
    template_name = "cecyrd/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Mandamos la meta al contexto para usarla en el HTML con {{ sla_ordinario }}
        context["sla_ordinario"] = SLA_ORDINARIO
        return context

class DashboardDataView(View):
    """API que agrupa registros evaluando SLAs dinámicos con métricas atómicas del SGC."""

    def get(self, request, *args, **kwargs):
        start_date = request.GET.get("start")
        end_date = request.GET.get("end")
        periodo_req = request.GET.get("periodo")

        queryset = Tramite.objects.filter(fecha_tramite__isnull=False)

        if start_date:
            queryset = queryset.filter(fecha_tramite__gte=start_date)
        if end_date:
            queryset = queryset.filter(fecha_tramite__lte=end_date)

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

        stats = (
            queryset.annotate(
                meta_aplicable=meta_dinamica, month=TruncMonth("fecha_tramite")
            )
            .values("month")
            .annotate(
                total=Count("folio"),
                analizados=Count("folio", filter=Q(tramo_disponible__isnull=False)),
                en_tiempo=Count(
                    "folio", filter=Q(tramo_disponible__lte=F("meta_aplicable"))
                ),
                rezago=Count(
                    "folio", filter=Q(tramo_disponible__gt=F("meta_aplicable"))
                ),
                promedio=Avg("tramo_disponible"),
            )
            .order_by("month")
        )

        MESES_ESPANOL = {
            1: "Ene",
            2: "Feb",
            3: "Mar",
            4: "Abr",
            5: "May",
            6: "Jun",
            7: "Jul",
            8: "Ago",
            9: "Sep",
            10: "Oct",
            11: "Nov",
            12: "Dic",
        }

        labels, totales, analizados_list, en_tiempo_list, rezago_list = (
            [],
            [],
            [],
            [],
            [],
        )
        cumplimiento, metas, motivos, promedios = [], [], [], []
        global_total, global_analizados, global_en_tiempo, global_rezago = (
            0,
            0,
            0,
            0,
        )

        for item in stats:
            if not item["month"]:
                continue

            raw_month = item["month"]
            if isinstance(raw_month, str):
                mes_dt = datetime.strptime(raw_month[:10], "%Y-%m-%d").date()
            elif hasattr(raw_month, "date"):
                mes_dt = raw_month.date()
            else:
                mes_dt = raw_month

            mes_es = f"{MESES_ESPANOL.get(mes_dt.month, '')} {mes_dt.year}"

            ultimo_dia = calendar.monthrange(mes_dt.year, mes_dt.month)[1]
            mes_fin = mes_dt.replace(day=ultimo_dia)

            global_total += item["total"]
            global_analizados += item["analizados"]
            global_en_tiempo += item["en_tiempo"]
            global_rezago += item["rezago"]

            promedio_val = item.get("promedio")
            promedio_dias = (
                promedio_val.total_seconds() / 86400 if promedio_val else 0
            )
            pct_cumplimiento = (
                (item["en_tiempo"] / item["analizados"] * 100)
                if item["analizados"] > 0
                else 0
            )

            meta_mes = SLA_ORDINARIO
            motivo_mes = "Ordinario"
            for p in PERIODOS_EXTRAORDINARIOS:
                inicio_p = datetime.strptime(p["inicio"], "%Y-%m-%d").date()
                fin_p = datetime.strptime(p["fin"], "%Y-%m-%d").date()

                if inicio_p <= mes_fin and fin_p >= mes_dt:
                    meta_mes = p["dias"]
                    motivo_mes = p["motivo"]

            labels.append(mes_es)
            totales.append(item["total"])
            analizados_list.append(item["analizados"])
            en_tiempo_list.append(item["en_tiempo"])
            rezago_list.append(item["rezago"])
            promedios.append(round(promedio_dias, 2))
            cumplimiento.append(round(pct_cumplimiento, 1))
            metas.append(meta_mes)
            motivos.append(motivo_mes)

        global_pct = (
            round((global_en_tiempo / global_analizados * 100), 1)
            if global_analizados > 0
            else 0
        )

        # NUEVO: Verificar si existe una revisión congelada para este periodo
        revision_data = None
        if periodo_req:
            revision = RevisionDireccion.objects.filter(periodo=periodo_req).first()
            if revision:
                revision_data = {
                    "conclusiones": revision.conclusiones,
                    "recomendaciones": revision.recomendaciones,
                    "pdf_url": revision.pdf_oficial.url
                    if revision.pdf_oficial
                    else None,
                    "congelado": True,
                    "kpis_congelados": {
                        "total_tramites": revision.total_tramites,
                        "analizados": revision.analizados,
                        "en_tiempo": revision.en_tiempo,
                        "rezago": revision.rezago,
                        "porcentaje_global": revision.porcentaje_global,
                    },
                }


        distribucion_qs = (
            queryset.filter(tramo_disponible__isnull=False)
            .annotate(dias=ExtractDay("tramo_disponible"))
            .values("dias")
            .annotate(cantidad=Count("folio"))
            .order_by("dias")
        )

        dias_dict = {i: 0 for i in range(16)}
        for item in distribucion_qs:
            dia = item["dias"]
            if dia is not None:
                if dia > 15:
                    dias_dict[15] += item["cantidad"]
                else:
                    dias_dict[int(dia)] += item["cantidad"]

        dist_labels = [f"{i} días" for i in range(15)] + ["15+ días"]
        dist_data = [dias_dict[i] for i in range(16)]


        return JsonResponse(
            {
                "labels": labels,
                "datasets": {
                    "totales": totales,
                    "analizados": analizados_list,
                    "en_tiempo": en_tiempo_list,
                    "rezago": rezago_list,
                    "promedios": promedios,
                    "cumplimiento": cumplimiento,
                    "metas": metas,
                    "motivos": motivos,
                },
                "kpis": {
                    "total_tramites": global_total,
                    "analizados": global_analizados,
                    "en_tiempo": global_en_tiempo,
                    "porcentaje_global": global_pct,
                    "rezago": global_rezago,
                },
                "revision": revision_data,
                "distribucion": {
                    "labels": dist_labels,
                    "data": dist_data
                }
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


class GuardarRevisionView(PermissionRequiredMixin, View):
    """Guarda los textos de la Revisión por la Dirección y genera el PDF oficial con gráficas inyectadas."""

    permission_required = "cecyrd.change_revisiondireccion"

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            periodo = data.get("periodo")

            revision, created = RevisionDireccion.objects.get_or_create(
                periodo=periodo,
                defaults={
                    "responsable": request.user,
                    "total_tramites": int(
                        data.get("kpis", {}).get("total_tramites", 0)
                    ),
                    "analizados": int(data.get("kpis", {}).get("analizados", 0)),
                    "en_tiempo": int(data.get("kpis", {}).get("en_tiempo", 0)),
                    "rezago": int(data.get("kpis", {}).get("rezago", 0)),
                    "porcentaje_global": float(
                        data.get("kpis", {}).get("porcentaje_global", 0)
                    ),
                },
            )

            revision.conclusiones = data.get("conclusiones", "")
            revision.recomendaciones = data.get("recomendaciones", "")
            revision.save()

            grafica_tendencia = data.get("grafica_tendencia", "")
            grafica_estres = data.get("grafica_estres", "")
            grafica_distribucion = data.get("grafica_distribucion", "") # NUEVO: Recibimos la imagen

            html_string = render_to_string(
                "cecyrd/reporte_sgc_pdf.html",
                {
                    "revision": revision,
                    "grafica_tendencia": grafica_tendencia,
                    "grafica_estres": grafica_estres,
                    "grafica_distribucion": grafica_distribucion, # NUEVO: La pasamos al PDF
                },
            )

            pdf_file = HTML(
                string=html_string, base_url=request.build_absolute_uri()
            ).write_pdf()

            nombre_archivo = f"Revision_SGC_{periodo}.pdf"
            revision.pdf_oficial.save(nombre_archivo, ContentFile(pdf_file), save=True)

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Revisión guardada y Expediente PDF con gráficas generado exitosamente.",
                }
            )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)


class ReporteSemanalView(TemplateView):
    template_name = "cecyrd/reporte_semanal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date_str = self.request.GET.get("start", "2026-05-01")
        end_date_str = self.request.GET.get("end", "2026-07-31")

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        qs = Tramite.objects.filter(
            fecha_tramite__gte=start_date,
            fecha_tramite__lte=end_date,
            tramo_disponible__isnull=False,
        )

        # KPIs Superiores
        total_analizados = qs.count()
        promedio_estatal = qs.aggregate(avg=Avg("tramo_disponible"))["avg"]
        promedio_dias_estatal = (
            round(promedio_estatal.total_seconds() / 86400, 1)
            if promedio_estatal
            else 0
        )

        # Gráfica Acumulada
        stats_distrito = (
            qs.values("distrito")
            .annotate(avg_tramo=Avg("tramo_disponible"))
            .order_by("distrito")
        )

        distritos_labels = []
        distritos_promedios = []

        for item in stats_distrito:
            distritos_labels.append(f"Distrito {item['distrito']}")
            val = (
                round(item["avg_tramo"].total_seconds() / 86400, 1)
                if item["avg_tramo"]
                else 0
            )
            distritos_promedios.append(val)

        # Gráfica Principal: Tendencia Semanal
        tendencia = (
            qs.annotate(semana=TruncWeek("fecha_tramite"))
            .values("semana", "distrito")
            .annotate(promedio=Avg("tramo_disponible"))
            .order_by("semana", "distrito")
        )

        semanas_set = sorted(
            list(set(item["semana"] for item in tendencia if item["semana"]))
        )

        # Diccionarios de meses
        MESES = {
            1: "Ene",
            2: "Feb",
            3: "Mar",
            4: "Abr",
            5: "May",
            6: "Jun",
            7: "Jul",
            8: "Ago",
            9: "Sep",
            10: "Oct",
            11: "Nov",
            12: "Dic",
        }
        MESES_MIN = {k: v.lower() for k, v in MESES.items()}

        semanas_labels = [f"Sem {s.day} {MESES.get(s.month)}" for s in semanas_set]

        data_d1 = {s: None for s in semanas_set}
        data_d2 = {s: None for s in semanas_set}
        data_d3 = {s: None for s in semanas_set}

        for item in tendencia:
            sem = item["semana"]
            if not sem:
                continue
            val = (
                round(item["promedio"].total_seconds() / 86400, 1)
                if item["promedio"]
                else None
            )
            d = item["distrito"]
            if d == 1:
                data_d1[sem] = val
            elif d == 2:
                data_d2[sem] = val
            elif d == 3:
                data_d3[sem] = val

        # Construcción de la tabla
        tabla_semanas = []
        for sem in semanas_set:
            fin_dt = sem + timedelta(days=6)
            inicio_str = f"lun {sem.day:02d}/{MESES_MIN.get(sem.month)}/{sem.year}"
            fin_str = (
                f"dom {fin_dt.day:02d}/{MESES_MIN.get(fin_dt.month)}/{fin_dt.year}"
            )
            label_larga = f"{inicio_str} - {fin_str}"

            tabla_semanas.append(
                {
                    "semana": label_larga,
                    "d1": data_d1[sem] if data_d1[sem] is not None else "-",
                    "d2": data_d2[sem] if data_d2[sem] is not None else "-",
                    "d3": data_d3[sem] if data_d3[sem] is not None else "-",
                }
            )

        context.update(
            {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "total_analizados": total_analizados,
                "promedio_estatal": promedio_dias_estatal,
                "chart_semanas_labels": json.dumps(semanas_labels),
                "chart_d1": json.dumps(list(data_d1.values())),
                "chart_d2": json.dumps(list(data_d2.values())),
                "chart_d3": json.dumps(list(data_d3.values())),
                "chart_distritos_labels": json.dumps(distritos_labels),
                "chart_distritos_promedios": json.dumps(distritos_promedios),
                "tabla_semanas": tabla_semanas,
                "tabla_semanas_json": json.dumps(tabla_semanas),
            }
        )
        return context


class ReporteSemanalPDFView(View):
    """Generador efímero de PDF en formato Horizontal (Landscape)"""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            context = {
                "start_date": start_date,
                "end_date": end_date,
                "total_analizados": data.get("total_analizados"),
                "promedio_estatal": data.get("promedio_estatal"),
                "img_tendencia": data.get("img_tendencia"),
                "img_barras": data.get("img_barras"),
                "tabla_semanas": data.get("tabla_semanas", []),
                "fecha_generacion": datetime.now(),
            }

            html_string = render_to_string("cecyrd/reporte_semanal_pdf.html", context)
            pdf_file = HTML(
                string=html_string, base_url=request.build_absolute_uri()
            ).write_pdf()

            response = HttpResponse(pdf_file, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="Desempeno_Semanal_{start_date}_al_{end_date}.pdf"'
            )
            return response

        except Exception as e:
            return HttpResponse(f"Error generando PDF: {str(e)}", status=400)
