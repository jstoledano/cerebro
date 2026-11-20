"""Vistas de consulta de la agenda Org-mode."""
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.agenda.services.data import (
    active_items, dashboard_metrics, items_for_range, load_payload,
)
from apps.agenda.services.pdf import generate_pdf


def _payload_or_error():
    try:
        return load_payload(), None
    except (FileNotFoundError, ValueError, OSError) as exc:
        return None, str(exc)


def _today():
    return timezone.localdate()


def _date_arg(request, key="date", default=None):
    value = request.GET.get(key)
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def _stamp_value(stamp, key="start"):
    return stamp.get(key) if isinstance(stamp, dict) else None


def _calendar_stamps(item):
    """Representa cada tarea como punto de atención, nunca como barra continua.

    SCHEDULED determina el día en que la actividad aparece en el calendario.
    DEADLINE se conserva en extendedProps para mostrar el vencimiento en el
    detalle. Si no existe SCHEDULED, se utiliza DEADLINE como fecha principal.
    Los timestamps independientes siguen siendo eventos puntuales.
    """
    scheduled = item.get("scheduled")
    deadline = item.get("deadline")
    if scheduled:
        return [(scheduled, "Programada")]
    if deadline:
        return [(deadline, "Vence")]
    return [
        (stamp, "Evento")
        for stamp in (item.get("timestamps") or [])
    ]


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        payload, error = _payload_or_error()
        if error:
            return render(request, "agenda/unavailable.html", {"error": error})
        today = _today()
        metrics = dashboard_metrics(payload, today)
        def present(items):
            result = []
            for original in items:
                item = dict(original)
                scheduled = item.get("scheduled") or {}
                deadline = item.get("deadline") or {}
                item["display_date"] = scheduled.get("start") or deadline.get("start") or ""
                item["deadline_display"] = deadline.get("start") or ""
                item["properties"] = item.get("properties") or {}
                result.append(item)
            return result

        recent = sorted(
            present([item for item in active_items(payload) if item.get("scheduled") or item.get("deadline")]),
            key=lambda item: (item.get("display_date") or "9999", item.get("title", "").casefold()),
        )[:10]
        return render(request, "agenda/dashboard.html", {
            "today": today, "payload": payload,
            "total_open": len(metrics["tasks"]),
            "overdue": present(metrics["overdue"]), "due_today": present(metrics["due_today"]),
            "upcoming": present(metrics["upcoming"]), "doing": present(metrics["doing"]),
            "recent": recent, "validation": payload.get("validation", {}),
            "generated_at": payload.get("generated_at", ""),
            "source_count": len(payload.get("source_files", [])),
        })


class DoingView(LoginRequiredMixin, View):
    """Listado de actividades DOING, ordenado por urgencia y vencimiento."""

    def get(self, request):
        payload, error = _payload_or_error()
        if error:
            return render(request, "agenda/unavailable.html", {"error": error})

        today = _today()
        items = [
            dict(item)
            for item in active_items(payload)
            if item.get("kind") == "task"
            and str(item.get("state") or "").upper() == "DOING"
        ]

        def ordering(item):
            scheduled = item.get("scheduled") or {}
            deadline = item.get("deadline") or {}
            scheduled_value = scheduled.get("start") or ""
            deadline_value = deadline.get("start") or ""
            reference = deadline_value or scheduled_value
            try:
                reference_date = date.fromisoformat(reference[:10]) if reference else None
            except ValueError:
                reference_date = None
            if reference_date is None:
                bucket = 3
            elif reference_date < today:
                bucket = 0
            elif reference_date == today:
                bucket = 1
            else:
                bucket = 2
            return (
                bucket,
                reference_date or date.max,
                scheduled_value or "9999-12-31",
                str((item.get("properties") or {}).get("PLAN", "")).casefold(),
                str(item.get("title", "")).casefold(),
            )

        items.sort(key=ordering)
        for item in items:
            scheduled = item.get("scheduled") or {}
            deadline = item.get("deadline") or {}
            item["scheduled_display"] = scheduled.get("start") or ""
            item["deadline_display"] = deadline.get("start") or ""
            item["properties"] = item.get("properties") or {}
            reference = item["deadline_display"] or item["scheduled_display"]
            try:
                reference_date = date.fromisoformat(reference[:10]) if reference else None
            except ValueError:
                reference_date = None
            item["urgency"] = (
                "Vencida" if reference_date and reference_date < today
                else "Hoy" if reference_date == today
                else "Próxima" if reference_date
                else "Sin fecha"
            )
        return render(request, "agenda/doing.html", {
            "today": today,
            "items": items,
            "item_count": len(items),
            "overdue_count": sum(1 for item in items if item["urgency"] == "Vencida"),
            "today_count": sum(1 for item in items if item["urgency"] == "Hoy"),
        })


class CalendarEventsView(LoginRequiredMixin, View):
    def get(self, request):
        payload, error = _payload_or_error()
        if error:
            return JsonResponse({"error": error}, status=503)
        start_raw = request.GET.get("start", "")[:10]
        end_raw = request.GET.get("end", "")[:10]
        try:
            start = date.fromisoformat(start_raw) if start_raw else _today()
            end = date.fromisoformat(end_raw) if end_raw else start + timedelta(days=45)
        except ValueError:
            return JsonResponse({"error": "Rango de fechas invalido."}, status=400)

        events = []
        for item in active_items(payload):
            for stamp, label in _calendar_stamps(item):
                raw_start = _stamp_value(stamp)
                if not raw_start:
                    continue
                try:
                    event_date = date.fromisoformat(raw_start[:10])
                except ValueError:
                    continue
                if not (start <= event_date < end):
                    continue
                all_day = "T" not in raw_start
                raw_end = _stamp_value(stamp, "end")
                event = {
                    "id": f"{item.get('id') or item.get('source')}:{item.get('line')}:{label}:{raw_start}",
                    "title": item.get("title") or "Actividad",
                    "start": raw_start,
                    "allDay": all_day,
                    "extendedProps": {
                        "taskId": item.get("id"),
                        "state": item.get("state") or "EVENT",
                        "source": item.get("source"),
                        "plan": (item.get("properties") or {}).get("PLAN", ""),
                        "scope": (item.get("properties") or {}).get("SCOPE", ""),
                        "owner": (item.get("properties") or {}).get("OWNER", ""),
                        "monitor": (item.get("properties") or {}).get("MONITOR", ""),
                        "operative": (item.get("properties") or {}).get("OPERATIVE", ""),
                        "deadline": _stamp_value(item.get("deadline")),
                        "dateKind": label,
                        "kind": item.get("kind"),
                        "priority": item.get("priority"),
                    },
                }
                if raw_end and raw_end != raw_start:
                    if all_day:
                        try:
                            event["end"] = (date.fromisoformat(raw_end[:10]) + timedelta(days=1)).isoformat()
                        except ValueError:
                            pass
                    else:
                        event["end"] = raw_end
                events.append(event)
        return JsonResponse(events, safe=False)


class AgendaListView(LoginRequiredMixin, View):
    def get(self, request):
        payload, error = _payload_or_error()
        if error:
            return render(request, "agenda/unavailable.html", {"error": error})
        period = request.GET.get("period", "day")
        target = _date_arg(request, default=_today())
        if period == "week":
            start = target - timedelta(days=target.weekday())
            end = start + timedelta(days=6)
        elif period == "range":
            start = target
            end = _date_arg(request, "end", start + timedelta(days=6))
            if end < start:
                end = start
        else:
            period = "day"
            start = end = target
        items = items_for_range(payload, start, end)
        groups = {}
        for item in items:
            day = date.fromisoformat(item["agenda_date"])
            groups.setdefault(day, []).append(item)
        return render(request, "agenda/agenda.html", {
            "period": period, "start": start, "end": end,
            "groups": sorted(groups.items()), "item_count": len(items),
        })


class AgendaPDFView(LoginRequiredMixin, View):
    def get(self, request):
        payload, error = _payload_or_error()
        if error:
            return HttpResponse(error, status=503, content_type="text/plain; charset=utf-8")
        period = request.GET.get("period", "day")
        target = _date_arg(request, default=_today())
        if period == "week":
            start = target - timedelta(days=target.weekday())
            end = start + timedelta(days=6)
        else:
            start = end = target
        items = items_for_range(payload, start, end)
        try:
            path = generate_pdf(items, start, end, Path(settings.AGENDA_OUTPUT_DIR))
        except (RuntimeError, OSError) as exc:
            return HttpResponse(str(exc), status=500, content_type="text/plain; charset=utf-8")
        return FileResponse(path.open("rb"), as_attachment=True, filename=path.name,
                            content_type="application/pdf")


class ICalendarView(LoginRequiredMixin, View):
    def get(self, request):
        path = Path(settings.AGENDA_OUTPUT_DIR) / "agenda.ics"
        if not path.is_file():
            return HttpResponse(
                "No existe agenda.ics. Ejecuta python manage.py agenda_export.",
                status=404, content_type="text/plain; charset=utf-8",
            )
        return FileResponse(path.open("rb"), as_attachment=True, filename="agenda.ics",
                            content_type="text/calendar; charset=utf-8")
