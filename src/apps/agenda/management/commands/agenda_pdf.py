"""Generate a daily or weekly PDF from the latest agenda export."""
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.agenda.services.data import load_payload, items_for_range
from apps.agenda.services.pdf import generate_pdf


class Command(BaseCommand):
    help = "Genera la agenda PDF diaria o semanal mediante XeLaTeX."

    def add_arguments(self, parser):
        parser.add_argument("--period", choices=("day", "week"), default="day")
        parser.add_argument("--date", dest="target_date", default=None)

    def handle(self, *args, **options):
        try:
            target = date.fromisoformat(options["target_date"]) if options["target_date"] else timezone.localdate()
            start = target if options["period"] == "day" else target - timedelta(days=target.weekday())
            end = start if options["period"] == "day" else start + timedelta(days=6)
            payload = load_payload()
            items = items_for_range(payload, start, end)
            path = generate_pdf(items, start, end, Path(settings.AGENDA_OUTPUT_DIR))
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(str(path)))
