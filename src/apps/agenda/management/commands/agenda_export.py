"""Export Org sources to JSON and iCalendar using Emacs batch."""
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Procesa los archivos Org y genera agenda.json, agenda.ics y manifest.json."

    def add_arguments(self, parser):
        parser.add_argument("--agenda-path", default=None)
        parser.add_argument("--output-dir", default=None)
        parser.add_argument("--skip-ics", action="store_true")
        parser.add_argument(
            "--file", action="append", dest="agenda_files", default=None,
            help="Archivo Org relativo a AGENDA_PATH. Puede repetirse.",
        )

    def _wsl_path(self, command, path):
        if os.name != "nt" or Path(command[0]).name.lower() not in {"wsl", "wsl.exe"}:
            return str(path)
        # Normalizar a barras para evitar que WSL consuma las barras invertidas
        # de rutas Windows antes de ejecutar wslpath.
        windows_path = str(path).replace("\\", "/")
        prefix = command[:-1]
        result = subprocess.run(
            prefix + ["--exec", "wslpath", "-a", windows_path],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise CommandError(f"No se pudo convertir la ruta para WSL: {result.stderr}")
        return result.stdout.strip()

    def _run_emacs(self, command, script, args):
        executable = shlex.split(command)
        if not executable:
            raise CommandError("AGENDA_EMACS_COMMAND esta vacio.")
        script_arg = self._wsl_path(executable, script)
        args = [self._wsl_path(executable, Path(arg)) if os.path.isabs(str(arg)) else str(arg)
                for arg in args]
        argv = executable + ["--batch", "-Q", "--script", script_arg, "--"] + args
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        if result.stdout:
            self.stdout.write(result.stdout.rstrip())
        if result.returncode:
            raise CommandError(result.stderr.strip() or "Emacs termino con error.")

    def _selected_files(self, agenda_path, requested_files):
        """Validate the explicit Org source allowlist and return relative paths."""
        configured = requested_files
        if configured is None:
            configured = getattr(settings, "AGENDA_FILES", [])
        if isinstance(configured, str):
            configured = [part.strip() for part in configured.split(",") if part.strip()]
        if not configured:
            raise CommandError(
                "AGENDA_FILES debe enumerar los archivos Org autorizados, "
                "por ejemplo PEC-2026.org,RFE.org. No se escanean directorios completos."
            )

        root = agenda_path.resolve()
        selected = []
        seen = set()
        for raw in configured:
            relative = Path(str(raw).strip())
            if relative.is_absolute() or ".." in relative.parts:
                raise CommandError(f"Ruta Org no permitida en AGENDA_FILES: {raw}")
            if relative.suffix.lower() != ".org":
                raise CommandError(f"La fuente debe ser un archivo .org: {raw}")
            candidate = (root / relative).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise CommandError(f"La fuente sale de AGENDA_PATH: {raw}") from exc
            if not candidate.is_file():
                raise CommandError(f"No existe el archivo Org configurado: {candidate}")
            normalized = candidate.relative_to(root).as_posix()
            if normalized in seen:
                raise CommandError(f"Archivo Org repetido en AGENDA_FILES: {normalized}")
            seen.add(normalized)
            selected.append(normalized)
        return selected

    def _git_revision(self, agenda_path):
        result = subprocess.run(
            ["git", "-C", str(agenda_path), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def handle(self, *args, **options):
        configured_path = options["agenda_path"] or getattr(settings, "AGENDA_PATH", None)
        if not configured_path:
            raise CommandError("Configura AGENDA_PATH en el archivo .env y core/settings.py.")
        agenda_path = Path(configured_path).expanduser().resolve()
        output_dir = Path(options["output_dir"] or settings.AGENDA_OUTPUT_DIR).expanduser().resolve()
        if not agenda_path.is_dir():
            raise CommandError(f"AGENDA_PATH no es un directorio: {agenda_path}")
        output_dir.mkdir(parents=True, exist_ok=True)
        selected_files = self._selected_files(agenda_path, options["agenda_files"])
        app_dir = Path(__file__).resolve().parents[2]
        org_dir = app_dir / "org"
        json_script = org_dir / "export-agenda.el"
        ics_script = org_dir / "export-icalendar.el"
        if not json_script.is_file():
            raise CommandError(f"No existe el exportador: {json_script}")
        command = getattr(settings, "AGENDA_EMACS_COMMAND", "emacs")
        with tempfile.TemporaryDirectory(prefix="agenda-export-") as temp:
            temp_dir = Path(temp)
            json_tmp = temp_dir / "agenda.json"
            ics_tmp = temp_dir / "agenda.ics"
            self._run_emacs(
                command, json_script,
                [str(agenda_path), str(json_tmp), *selected_files],
            )
            if not json_tmp.is_file():
                raise CommandError("Emacs no produjo agenda.json.")
            payload = json.loads(json_tmp.read_text(encoding="utf-8"))
            validation = payload.get("validation", {})
            if not validation.get("valid", False):
                missing = len(validation.get("missing_ids", []))
                duplicates = len(validation.get("duplicate_ids", {}))
                self.stdout.write(self.style.WARNING(
                    f"Validacion: {missing} tareas sin ID; {duplicates} IDs duplicados."
                ))
            if not options["skip_ics"]:
                try:
                    self._run_emacs(
                        command, ics_script,
                        [str(agenda_path), str(ics_tmp), *selected_files],
                    )
                except CommandError as exc:
                    self.stdout.write(self.style.WARNING(f"ICS no generado: {exc}"))
            (output_dir / "agenda.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            if ics_tmp.is_file():
                (output_dir / "agenda.ics").write_bytes(ics_tmp.read_bytes())
        manifest = {
            "generated_at": timezone.localtime().isoformat(),
            "schema_version": payload.get("schema_version"),
            "agenda_path": str(agenda_path),
            "source_files": selected_files,
            "git_commit": self._git_revision(agenda_path),
            "item_count": payload.get("item_count", 0),
            "task_count": payload.get("task_count", 0),
            "event_count": payload.get("event_count", 0),
            "validation": payload.get("validation", {}),
            "ics_generated": (output_dir / "agenda.ics").is_file(),
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self.stdout.write(self.style.SUCCESS(
            f"Agenda actualizada: {manifest['task_count']} tareas, "
            f"{manifest['event_count']} eventos. Salida: {output_dir}"
        ))
