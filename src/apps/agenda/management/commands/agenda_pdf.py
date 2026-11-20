"""Generar o reutilizar el PDF institucional de lunes a domingo."""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.agenda.services.weekly import get_or_create_weekly_pdf


class Command(BaseCommand):
    help = "Obtiene la agenda semanal (lunes a domingo); la genera si falta."

    def add_arguments(self, parser):
        parser.add_argument("--period", choices=("week",), default="week")
        parser.add_argument("--date", dest="target_date", default=None)
        parser.add_argument("--force", action="store_true",
                            help="Regenerar explicitamente el PDF semanal existente.")

    def handle(self, *args, **options):
        try:
            target = (date.fromisoformat(options["target_date"])
                      if options["target_date"] else timezone.localdate())
            path = get_or_create_weekly_pdf(target, force=options["force"])
        except (ValueError, FileNotFoundError, OSError, RuntimeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(str(path)))
