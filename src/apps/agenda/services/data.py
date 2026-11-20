"""Lectura y seleccion de compromisos a partir de Org-mode.

La agenda selecciona tareas por atencion temporal; el repositorio Org conserva
las fechas y la prioridad. No se crean estados ni datos derivados persistentes.
"""
import json
from copy import copy
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings

TERMINAL_STATES = {"DONE", "CANCELLED", "CANCELED", "OMITTED", "OMITED"}
PENDING_STATES = {"TODO"}
PRIORITY_WINDOWS = {"A": 14, "B": 7, "C": 3, "": 1}
PRIORITY_ORDER = {"A": 0, "B": 1, "C": 2, "": 3}


def output_dir():
    return Path(settings.AGENDA_OUTPUT_DIR)


def load_payload():
    path = output_dir() / "agenda.json"
    if not path.is_file():
        raise FileNotFoundError(f"No existe {path}. Ejecuta: python manage.py agenda_export")
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("schema_version") != 1:
        raise ValueError("Version de agenda.json no compatible.")
    if not isinstance(payload.get("items"), list):
        raise ValueError("agenda.json no contiene una coleccion 'items' valida.")
    return payload


def stamp_date(stamp):
    if not isinstance(stamp, dict) or not stamp.get("start"):
        return None
    value = stamp["start"]
    try:
        return datetime.fromisoformat(value).date() if "T" in value else date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def active_items(payload):
    return [
        item for item in payload.get("items", [])
        if str(item.get("state") or "").upper() not in TERMINAL_STATES
    ]


def pending_tasks(payload):
    """Solo tareas TODO; el estado DOING se retiro de los archivos fuente."""
    return [
        item for item in payload.get("items", [])
        if item.get("kind") == "task" and str(item.get("state") or "").upper() in PENDING_STATES
    ]


def priority_code(item):
    value = str(item.get("priority") or "").strip().upper()
    return value if value in {"A", "B", "C"} else ""


def priority_window(item):
    return PRIORITY_WINDOWS[priority_code(item)]


def priority_label(item):
    return {"A": "Alta · A", "B": "Media · B", "C": "Baja · C", "": "Sin prioridad"}[priority_code(item)]


def item_date(item):
    return stamp_date(item.get("scheduled")) or deadline_date(item) or _first_timestamp_date(item)


def deadline_date(item):
    return stamp_date(item.get("deadline"))


def next_review_date(item):
    """Propiedad Org opcional, sin modificar el esquema de exportacion."""
    raw = (item.get("properties") or {}).get("NEXT_REVIEW")
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw).strip()[:10])
    except ValueError:
        return None


def _first_timestamp_date(item):
    for stamp in item.get("timestamps") or []:
        day = stamp_date(stamp)
        if day:
            return day
    return None


def dated_occurrences(item):
    found = {}
    for key, label in (("scheduled", "Programada"), ("deadline", "Vence")):
        current = stamp_date(item.get(key))
        if current:
            found.setdefault(current, []).append(label)
    if not found:
        for stamp in item.get("timestamps") or []:
            current = stamp_date(stamp)
            if current:
                found.setdefault(current, []).append("Evento")
    return [(day, "/".join(labels)) for day, labels in sorted(found.items())]


def attention_reason(item, target):
    """Motivo operativo para consultar una tarea TODO en una fecha.

    A: 14 dias de anticipacion al DEADLINE; B: 7; C: 3; sin prioridad: 1.
    El dia SCHEDULED se muestra como hito de inicio. NEXT_REVIEW, si existe,
    se mantiene pendiente desde esa fecha hasta que se actualice en Org.
    Las vencidas se gestionan en su bloque propio y quedan fuera de 'Hoy'.
    """
    if item.get("kind") != "task" or str(item.get("state") or "").upper() != "TODO":
        return None
    scheduled = stamp_date(item.get("scheduled"))
    deadline = deadline_date(item)
    if deadline and target > deadline:
        return None
    if scheduled and deadline and deadline < scheduled:
        return None

    review = next_review_date(item)
    if review and review <= target:
        return "Revisar"
    if scheduled == target:
        return "Programada/Vence" if deadline == target else "Inicia"
    if scheduled and target < scheduled:
        return None
    if deadline:
        days_left = (deadline - target).days
        if 0 <= days_left <= priority_window(item):
            return "Vence hoy" if days_left == 0 else f"Vence en {days_left} d"
    return None


def _focus_sort_key(item):
    return (
        deadline_date(item) or date.max,
        PRIORITY_ORDER[priority_code(item)],
        str((item.get("properties") or {}).get("PLAN", "")).casefold(),
        str(item.get("title") or "").casefold(),
    )


def todo_items_for_day(payload, target):
    """Seleccion pequena de tareas TODO que merecen atencion en 'target'."""
    return sorted(
        [item for item in pending_tasks(payload) if attention_reason(item, target)],
        key=_focus_sort_key,
    )


def _occurrence(item, current, label):
    occurrence = copy(item)
    occurrence["agenda_date"] = current.isoformat()
    occurrence["date_kind"] = label
    occurrence["deadline_display"] = (item.get("deadline") or {}).get("start", "")
    occurrence["scheduled_display"] = (item.get("scheduled") or {}).get("start", "")
    occurrence["display_date"] = occurrence["scheduled_display"] or occurrence["deadline_display"] or current.isoformat()
    occurrence["properties"] = item.get("properties") or {}
    occurrence["priority_label"] = priority_label(item)
    return occurrence


def _weekly_attention_anchor(item, start, end):
    """Una unica aparicion durante el periodo, anclada a un hito relevante."""
    scheduled = stamp_date(item.get("scheduled"))
    deadline = deadline_date(item)
    review = next_review_date(item)
    if scheduled and start <= scheduled <= end and attention_reason(item, scheduled):
        return scheduled, attention_reason(item, scheduled)
    if deadline and start <= deadline <= end and attention_reason(item, deadline):
        return deadline, attention_reason(item, deadline)
    if review:
        candidate = max(start, review)
        if candidate <= end and attention_reason(item, candidate):
            return candidate, "Revisar"
    if deadline:
        candidate = max(start, deadline - timedelta(days=priority_window(item)))
        if candidate <= end and attention_reason(item, candidate):
            return candidate, attention_reason(item, candidate)
    return None


def items_for_range(payload, start, end, include_terminal=False):
    """Seleccion diaria/semanal consistente con el dashboard, sin duplicados.

    Para cada tarea TODO aparece la primera fecha de atencion pertinente en el
    periodo, dando prioridad a inicios y vencimientos expresos.
    """
    items = payload.get("items", []) if include_terminal else active_items(payload)
    selected = []
    for item in items:
        if item.get("kind") == "task" and str(item.get("state") or "").upper() in PENDING_STATES:
            anchor = _weekly_attention_anchor(item, start, end)
            if anchor:
                selected.append(_occurrence(item, *anchor))
            continue
        for current, label in dated_occurrences(item):
            if start <= current <= end:
                selected.append(_occurrence(item, current, label))
    return sorted(selected, key=lambda item: (
        item.get("agenda_date", ""),
        deadline_date(item) or date.max,
        PRIORITY_ORDER[priority_code(item)],
        str(item.get("title") or "").casefold(),
    ))


def dashboard_metrics(payload, today):
    """Dashboard con radar identico al PDF semanal de lunes a domingo.

    El radar presenta los siguientes cinco hitos despues del domingo de la
    semana consultada. Reutiliza la misma seleccion y el mismo orden del PDF.
    """
    tasks = pending_tasks(payload)
    overdue = [item for item in tasks if deadline_date(item) and deadline_date(item) < today]
    due_today = todo_items_for_day(payload, today)
    _, week_end = week_bounds(today)
    upcoming = weekly_radar_items(payload, week_end, limit=5)
    return {"tasks": tasks, "overdue": overdue, "due_today": due_today, "upcoming": upcoming}



def week_bounds(target):
    """Semana civil institucional: lunes 00:00 a domingo 23:59."""
    monday = target - timedelta(days=target.weekday())
    return monday, monday + timedelta(days=6)


def weekly_overdue_items(payload, cutoff):
    """Pendientes vencidos antes de la fecha de generacion del documento."""
    return sorted(
        [item for item in pending_tasks(payload)
         if deadline_date(item) and deadline_date(item) < cutoff],
        key=lambda item: (
            deadline_date(item),
            PRIORITY_ORDER[priority_code(item)],
            str(item.get("title") or "").casefold(),
        ),
    )


def weekly_radar_items(payload, week_end, limit=5):
    """Cinco tareas distintas con el siguiente hito posterior al domingo.

    El horizonte avanza automaticamente cuando faltan tareas en la siguiente
    semana. Ante una misma fecha, vencimientos preceden a inicios y luego
    se ordena por prioridad. Se conserva solo el proximo hito de cada tarea.
    """
    if limit <= 0:
        return []
    candidates = []
    for item in pending_tasks(payload):
        milestones = []
        for key, label, precedence in (
            ("deadline", "Vence", 0),
            ("scheduled", "Inicia", 1),
        ):
            day = stamp_date(item.get(key))
            if day is not None and day > week_end:
                milestones.append((day, precedence, label))
        if not milestones:
            continue
        day, precedence, label = min(milestones)
        candidates.append((
            day,
            precedence,
            PRIORITY_ORDER[priority_code(item)],
            str(item.get("title") or "").casefold(),
            _occurrence(item, day, label),
        ))
    candidates.sort(key=lambda row: row[:-1])
    return [row[-1] for row in candidates[:limit]]
