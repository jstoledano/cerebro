"""Cache atomica del PDF semanal compartida por navegador y comando Django.

Los PDFs de lunes-domingo permanecen inmutables durante la semana. Solo el
comando --force puede sustituir un PDF que ya existe.
"""
from contextlib import contextmanager
from datetime import date
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.utils import timezone

from apps.agenda.services.data import (
    items_for_range, load_payload, week_bounds, weekly_overdue_items,
    weekly_radar_items,
)
from apps.agenda.services.pdf import generate_pdf


def weekly_pdf_path(target: date, output_dir=None) -> Path:
    start, end = week_bounds(target)
    directory = Path(output_dir or settings.AGENDA_OUTPUT_DIR).resolve()
    return directory / f"agenda-{start:%Y%m%d}-{end:%Y%m%d}.pdf"


def _pdf_exists(path: Path) -> bool:
    """Un PDF existente debe tener su cabecera valida y contenido no vacio."""
    try:
        if not path.is_file() or path.stat().st_size < 100:
            return False
        with path.open("rb") as file:
            return file.read(5) == b"%PDF-"
    except OSError:
        return False


@contextmanager
def _lock_pdf(path: Path):
    """Bloqueo interproceso con biblioteca estandar (Windows y Linux)."""
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def get_or_create_weekly_pdf(
    target: date | None = None, *, force: bool = False,
    payload: dict | None = None, output_dir=None,
) -> Path:
    """Devuelve el PDF existente o compila una sola copia de forma atomica.

    La primera solicitud de cualquier dia de la semana genera el PDF si falta.
    El cron de los lunes puede invocar el comando para precalentar el cache.
    Una actualizacion de agenda.json no reescribe PDFs ya publicados.
    """
    target = target or timezone.localdate()
    start, end = week_bounds(target)
    path = weekly_pdf_path(target, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not force and _pdf_exists(path):
        return path

    lock_path = path.with_suffix(".lock")
    with _lock_pdf(lock_path):
        # Otra peticion puede haber generado el documento durante la espera.
        if not force and _pdf_exists(path):
            return path
        data = payload if payload is not None else load_payload()
        cutoff = timezone.localdate()
        with TemporaryDirectory(prefix=f".{path.stem}-", dir=path.parent) as temporary:
            generated = generate_pdf(
                items_for_range(data, start, end), start, end, Path(temporary),
                overdue=weekly_overdue_items(data, cutoff),
                radar=weekly_radar_items(data, end, limit=5),
                cutoff=cutoff,
            )
            if not _pdf_exists(generated):
                raise RuntimeError("La generacion de la agenda semanal produjo un PDF invalido.")
            os.replace(generated, path)
    return path
