"""Vistas de consulta de la agenda Org-mode."""
import json
import subprocess
from datetime import date, datetime, timedelta
from urllib.parse import urlencode
from pathlib import Path

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.decorators import method_decorator

from apps.agenda.services.data import (
    active_items, attention_reason, dashboard_metrics, deadline_date,
    items_for_range, load_payload, pending_tasks,
    priority_code, priority_label, stamp_date, todo_items_for_day, week_bounds, PENDING_STATES,
)
from apps.agenda.services.weekly import get_or_create_weekly_pdf
from apps.agenda.services.indicators import project_indicators
from apps.agenda.services.tasks import task_detail
from apps.agenda.services.org_writer import change_task_state, StateChangeError


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
    """Hitos puntuales para tareas pendientes, sin barras de intervalo."""
    scheduled = item.get("scheduled")
    deadline = item.get("deadline")
    if item.get("kind") == "task" and str(item.get("state") or "").upper() in PENDING_STATES:
        if scheduled and deadline:
            if _stamp_value(scheduled) == _stamp_value(deadline):
                return [(scheduled, "Programada/Vence")]
            return [(scheduled, "Programada"), (deadline, "Vence")]
        if scheduled:
            return [(scheduled, "Programada")]
        if deadline:
            return [(deadline, "Vence")]
    if scheduled:
        return [(scheduled, "Programada")]
    if deadline:
        return [(deadline, "Vence")]
    return [(stamp, "Evento") for stamp in (item.get("timestamps") or [])]


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
                item["priority_label"] = priority_label(item)
                result.append(item)
            return result

        overdue = present(metrics["overdue"])
        overdue.sort(key=lambda item: (
            item.get("deadline_display") or "9999-12-31",
            str(item.get("priority") or "Z"),
            str(item.get("title") or "").casefold(),
        ))
        upcoming = present(metrics["upcoming"])
        for item in upcoming:
            item["next_milestone_date"] = item.get("agenda_date") or ""
            item["next_milestone_label"] = item.get("date_kind") or ""
        _, week_end = week_bounds(today)
        radar_start = week_end + timedelta(days=1)
        radar_end = (date.fromisoformat(upcoming[-1]["next_milestone_date"])
                     if upcoming else None)

        return render(request, "agenda/dashboard.html", {
            "today": today, "payload": payload,
            "total_open": len(metrics["tasks"]),
            "overdue": overdue, "due_today": present(metrics["due_today"]),
            "upcoming": upcoming,
            "radar_start": radar_start,
            "radar_end": radar_end,
            "validation": payload.get("validation", {}),
            "generated_at": payload.get("generated_at", ""),
            "source_count": len(payload.get("source_files", [])),
            "project_indicators": project_indicators(payload, today),
            "can_edit_agenda": bool(request.user.is_authenticated and request.user.is_staff),
        })


class PendingTasksView(LoginRequiredMixin, View):
    """Inventario general, consultable y filtrable, sin sobrecargar el dashboard."""
    def get(self, request):
        payload, error = _payload_or_error()
        if error:
            return render(request, "agenda/unavailable.html", {"error": error})
        today = _today()
        all_items = pending_tasks(payload)
        radar_ids = {item.get("id") for item in dashboard_metrics(payload, today)["upcoming"]}
        q = request.GET.get("q", "").strip()[:120]
        plan = request.GET.get("plan", "").strip()[:40]
        priority = request.GET.get("priority", "").strip().upper()
        if priority not in {"", "A", "B", "C", "NONE"}:
            priority = ""
        all_plans = sorted({
            str((item.get("properties") or {}).get("PLAN") or "").strip()
            for item in all_items
            if (item.get("properties") or {}).get("PLAN")
        }, key=str.casefold)
        selected = []
        for original in all_items:
            props = original.get("properties") or {}
            if plan and str(props.get("PLAN") or "").casefold() != plan.casefold():
                continue
            code = priority_code(original)
            if priority and code != ("" if priority == "NONE" else priority):
                continue
            if q:
                haystack = " ".join(str(part or "") for part in (
                    original.get("id"), original.get("title"), original.get("body"),
                    props.get("PLAN"), props.get("OWNER"), props.get("OPERATIVE"),
                )).casefold()
                if q.casefold() not in haystack:
                    continue
            item = dict(original)
            item["properties"] = props
            item["scheduled_display"] = _stamp_value(item.get("scheduled")) or ""
            item["deadline_display"] = _stamp_value(item.get("deadline")) or ""
            item["priority_label"] = priority_label(item)
            due = deadline_date(item)
            start = stamp_date(item.get("scheduled"))
            if due and due < today:
                rank, label = 0, "Vencida"
            elif attention_reason(item, today):
                rank, label = 1, "Atencion hoy"
            elif original.get("id") in radar_ids:
                rank, label = 2, "En el radar"
            else:
                rank, label = 3, "Pendiente"
            item["attention_label"] = label
            item["_sort"] = (rank, due or date.max,
                              {"A": 0, "B": 1, "C": 2, "": 3}[code],
                              start or date.max, str(item.get("title") or "").casefold())
            selected.append(item)
        selected.sort(key=lambda item: item["_sort"])
        page_obj = Paginator(selected, 25).get_page(request.GET.get("page"))
        filters = {key: value for key, value in (("q", q), ("plan", plan), ("priority", priority)) if value}
        page_query = urlencode(filters)
        return render(request, "agenda/pending.html", {
            "today": today, "page_obj": page_obj,
            "item_count": len(selected), "total_count": len(all_items),
            "q": q, "plan": plan, "priority": priority,
            "plans": all_plans, "page_query": page_query,
            "can_edit_agenda": bool(request.user.is_authenticated and request.user.is_staff),
        })


class CalendarEventsView(LoginRequiredMixin, View):
    def get(self, request):
        payload, error = _payload_or_error()
        if error:
            return JsonResponse({"error": error}, status=503)
        # El mismo endpoint alimenta el calendario y el panel del día elegido.
        if "focus" in request.GET:
            try:
                focus_date = date.fromisoformat(request.GET["focus"])
            except ValueError:
                return JsonResponse({"error": "Fecha seleccionada inválida."}, status=400)
            selected = []
            for item in todo_items_for_day(payload, focus_date):
                props = item.get("properties") or {}
                selected.append({
                    "id": item.get("id") or "",
                    "title": item.get("title") or "Actividad",
                    "state": "TODO",
                    "plan": props.get("PLAN") or item.get("source") or "",
                    "owner": props.get("OWNER") or "",
                    "operative": props.get("OPERATIVE") or "",
                    "monitor": props.get("MONITOR") or "",
                    "scheduled": _stamp_value(item.get("scheduled")) or "",
                    "deadline": _stamp_value(item.get("deadline")) or "",
                    "source": item.get("source") or "",
                    "priority": priority_code(item),
                    "priority_label": priority_label(item),
                    "attention": attention_reason(item, focus_date),
                })
            return JsonResponse(selected, safe=False)

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
                is_todo = str(item.get("state") or "").upper() in PENDING_STATES
                is_todo = is_todo and item.get("kind") == "task"
                title = item.get("title") or "Actividad"
                if is_todo:
                    prefix = {"Programada": "Inicio", "Vence": "Vence", "Programada/Vence": "Hoy"}.get(label, label)
                    task_id = str(item.get("id") or "")
                    if task_id and not title.casefold().startswith(task_id.casefold()):
                        title = f"{task_id} · {title}"
                    title = f"{prefix} · {title[:76]}{'…' if len(title) > 76 else ''}"
                event = {
                    "id": f"{item.get('id') or item.get('source')}:{item.get('line')}:{label}:{raw_start}",
                    "title": title,
                    "start": raw_start,
                    "allDay": all_day,
                    "extendedProps": {
                        "taskId": item.get("id"),
                        "state": "TODO" if is_todo else (item.get("state") or "EVENT"),
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
                        "fullTitle": item.get("title") or "Actividad",
                    },
                }
                if not is_todo and raw_end and raw_end != raw_start:
                    if all_day:
                        try:
                            event["end"] = (date.fromisoformat(raw_end[:10]) + timedelta(days=1)).isoformat()
                        except ValueError:
                            pass
                    else:
                        event["end"] = raw_end
                events.append(event)

        today = _today()
        if start <= today < end:
            # Solo un marcador compacto para los TODO activos de hoy.
            count = len(todo_items_for_day(payload, today))
            if count:
                events.append({
                    "id": "agenda-todo-vigentes-hoy",
                    "title": f"{count} pendientes vigentes",
                    "start": today.isoformat(),
                    "allDay": True,
                    "extendedProps": {"isTodoSummary": True, "state": "TODO"},
                })
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
    """Servir el PDF semanal existente; generarlo si aun no existe."""

    def get(self, request):
        period = request.GET.get("period", "week")
        if period != "week":
            return HttpResponse(
                "Solo esta disponible la agenda semanal en PDF.",
                status=400, content_type="text/plain; charset=utf-8",
            )
        target = _date_arg(request, default=_today())
        try:
            path = get_or_create_weekly_pdf(target)
            return FileResponse(
                path.open("rb"), as_attachment=True, filename=path.name,
                content_type="application/pdf",
            )
        except (RuntimeError, OSError, ValueError) as exc:
            return HttpResponse(
                str(exc), status=503, content_type="text/plain; charset=utf-8",
            )


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


class TaskDetailView(View):
    """Ficha publica, con propiedades explicitamente permitidas."""
    def get(self, request):
        task_id = request.GET.get('id', '').strip()[:120]
        if not task_id:
            return JsonResponse({'error': 'Indica el ID de la actividad.'}, status=400)
        payload, error = _payload_or_error()
        if error:
            return JsonResponse({'error': error}, status=503)
        matches = [item for item in payload['items'] if item.get('kind') == 'task' and item.get('id') == task_id]
        if len(matches) != 1:
            return JsonResponse({'error': 'Actividad inexistente o ID duplicado.'}, status=404)
        data = task_detail(matches[0])
        data['can_edit'] = bool(request.user.is_authenticated and request.user.is_staff)
        return JsonResponse(data)


@method_decorator(csrf_protect, name='dispatch')
class TaskStateView(View):
    """Endpoint de escritura: solo personal autorizado, nota obligatoria."""
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Se requiere iniciar sesion.'}, status=401)
        if not request.user.is_staff:
            return JsonResponse({'error': 'Se requieren permisos de personal.'}, status=403)
        if len(request.body) > 12000:
            return JsonResponse({'error': 'Solicitud demasiado grande.'}, status=413)
        try:
            data = json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError('El cuerpo debe ser un objeto JSON.')
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({'error': 'JSON invalido.'}, status=400)
        try:
            result = change_task_state(data.get('id', ''), data.get('state', ''), data.get('note', ''))
        except StateChangeError as exc:
            return JsonResponse({'error': str(exc)}, status=409)
        except (OSError, subprocess.SubprocessError) as exc:
            return JsonResponse({'error': 'Error de sistema al actualizar la actividad.'}, status=503)
        return JsonResponse({'ok': True, **result})
