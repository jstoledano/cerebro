"""Convierte DOING a TODO únicamente en encabezados de fuentes Org autorizadas."""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

PATTERN = re.compile(rb"(?m)^(\*+[ \t]+)DOING(?=[ \t])")


class Command(BaseCommand):
    help = "Normaliza DOING a TODO en AGENDA_FILES, preservando el resto del archivo."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Aplicar los cambios (por defecto, vista previa).")

    def handle(self, *args, **options):
        root = Path(getattr(settings, "AGENDA_PATH", "") or "").expanduser().resolve()
        names = getattr(settings, "AGENDA_FILES", [])
        if isinstance(names, str):
            names = [name.strip() for name in names.split(",") if name.strip()]
        if not root.is_dir() or not names:
            raise CommandError("Configura AGENDA_PATH y AGENDA_FILES.")
        selected = []
        for name in names:
            path = (root / name).resolve()
            if path.suffix.lower() != ".org" or not path.is_file() or not path.is_relative_to(root):
                raise CommandError(f"Fuente Org inválida: {name}")
            selected.append(path)
        total = 0
        for path in dict.fromkeys(selected):
            original = path.read_bytes()
            changed, count = PATTERN.subn(rb"\1TODO", original)
            total += count
            self.stdout.write(f"{path.name}: {count} encabezados DOING")
            if options["apply"] and count:
                path.write_bytes(changed)
        label = "Convertidas" if options["apply"] else "Encontradas"
        self.stdout.write(self.style.SUCCESS(f"{label}: {total} actividades. ") +
                          ("" if options["apply"] else "Ejecuta con --apply para modificar las fuentes."))
