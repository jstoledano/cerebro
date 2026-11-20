"""Lectura y consultas sobre el JSON generado por Org-mode."""
import json
from copy import copy
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings

TERMINAL_STATES = {"DONE", "CANCELLED", "CANCELED", "OMITTED", "OMITED"}


def output_dir():
    return Path(settings.AGENDA_OUTPUT_DIR)


def load_payload():
    path = output_dir() / "agenda.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"No existe {path}. Ejecuta: python manage.py agenda_export"
        )
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("schema_version") != 1:
        raise ValueError("Version de agenda.json no compatible.")
    if not isinstance(payload.get("items"), list):
        raise ValueError("agenda.json no contiene una colección 'items' válida.")
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


def item_date(item):
    """Fecha principal de la tarea: SCHEDULED, después DEADLINE y timestamps."""
    return (
        stamp_date(item.get("scheduled"))
        or stamp_date(item.get("deadline"))
        or _first_timestamp_date(item)
    )


def deadline_date(item):
    return stamp_date(item.get("deadline"))


def _first_timestamp_date(item):
    stamps = item.get("timestamps") or []
    return next((stamp_date(stamp) for stamp in stamps if stamp_date(stamp)), None)


def dated_occurrences(item):
    """Return distinct scheduled/deadline/timestamp dates with their labels."""
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


def items_for_range(payload, start, end, include_terminal=False):
    items = payload.get("items", []) if include_terminal else active_items(payload)
    selected = []
    for item in items:
        for current, label in dated_occurrences(item):
            if start <= current <= end:
                occurrence = copy(item)
                occurrence["agenda_date"] = current.isoformat()
                occurrence["date_kind"] = label
                occurrence["deadline_display"] = (item.get("deadline") or {}).get("start", "")
                occurrence["scheduled_display"] = (item.get("scheduled") or {}).get("start", "")
                occurrence["display_date"] = occurrence["scheduled_display"] or occurrence["deadline_display"] or current.isoformat()
                occurrence["properties"] = item.get("properties") or {}
                selected.append(occurrence)
    return sorted(
        selected,
        key=lambda item: (
            item.get("agenda_date", ""),
            ((item.get("scheduled") or {}).get("start") or ""),
            item.get("title", "").casefold(),
        ),
    )


def dashboard_metrics(payload, today):
    tasks = [item for item in active_items(payload) if item.get("kind") == "task"]
    overdue = [item for item in tasks if deadline_date(item) and deadline_date(item) < today]
    due_today = [item for item in tasks if any(day == today for day, _ in dated_occurrences(item))]
    upcoming = [
        item for item in tasks
        if any(today < day <= today + timedelta(days=7) for day, _ in dated_occurrences(item))
    ]
    doing = [item for item in tasks if item.get("state") == "DOING"]
    return {"tasks": tasks, "overdue": overdue, "due_today": due_today,
            "upcoming": upcoming, "doing": doing}
