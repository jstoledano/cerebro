import csv
import zipfile
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.pusinex.views import (
    SECCIONES_VNM2026_COBERTURA,
    get_vnm2026_statistics,
)


VNM2026_DIRECTORY = Path(settings.MEDIA_ROOT) / "pusinex" / "vnm2026"

VNM2026_FILENAME = "29_vnm2026_distrito_{district:02d}.zip"

MANIFEST_FILENAME = "MANIFIESTO.csv"


def build_manifest(entries):
    output = StringIO(newline="")

    writer = csv.writer(output)

    writer.writerow(
        [
            "distrito",
            "municipio",
            "seccion",
            "tipo",
            "fecha_revision",
            "nombre_archivo",
            "estado",
        ]
    )

    for entry in entries:
        section = entry["section"]
        pusinex = entry["pusinex"]

        writer.writerow(
            [
                f"{section.distrito.distrito:02d}",
                f"{section.municipio.municipio:03d}",
                f"{section.seccion:04d}",
                section.get_tipo_display(),
                pusinex.f_act.isoformat() if pusinex else "",
                entry["filename"],
                entry["status"],
            ]
        )

    return output.getvalue()


def validate_pdf(entry):
    """
    Comprueba que el archivo exista y tenga cabecera PDF.
    """
    pusinex = entry["pusinex"]

    if pusinex is None or not pusinex.archivo:
        return False

    storage = pusinex.archivo.storage

    if not storage.exists(pusinex.archivo.name):
        return False

    with storage.open(pusinex.archivo.name, "rb") as fh:
        signature = fh.read(5)

    return signature == b"%PDF-"


class Command(BaseCommand):
    help = "Genera los paquetes ZIP distritales definitivos de la VNM 2026."

    def handle(self, *args, **options):
        VNM2026_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        districts = get_vnm2026_statistics(SECCIONES_VNM2026_COBERTURA)

        if not districts:
            raise CommandError(
                "No se encontraron secciones para la VNM 2026."
            )

        self.stdout.write(
            self.style.NOTICE(
                "Generando paquetes VNM 2026..."
            )
        )

        for district in districts:
            district_number = district["district"].distrito

            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"Distrito {district_number:02d}"
                )
            )

            included = []
            rural = []
            errors = []

            for entry in district["sections"]:
                status = entry["status"]

                if status == "RURAL":
                    rural.append(entry)
                    continue

                if status != "INCLUIDO":
                    errors.append(entry)
                    continue

                if not validate_pdf(entry):
                    entry["status"] = "PDF_INVALIDO"
                    errors.append(entry)
                    continue

                included.append(entry)

            self.stdout.write(
                f"  Seleccionadas: {district['selected']}"
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Con PUSINEX válido: {len(included)}"
                )
            )

            self.stdout.write(
                f"  Rurales: {len(rural)}"
            )

            if errors:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Con incidencias: {len(errors)}"
                    )
                )

                for entry in errors:
                    section = entry["section"]

                    self.stdout.write(
                        self.style.WARNING(
                            "    "
                            f"Sección {section.seccion:04d}: "
                            f"{entry['status']}"
                        )
                    )

            target_path = (
                VNM2026_DIRECTORY
                / VNM2026_FILENAME.format(
                    district=district_number
                )
            )

            temporary_path = None

            try:
                with NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{target_path.stem}_",
                    suffix=".tmp",
                    dir=VNM2026_DIRECTORY,
                    delete=False,
                ) as temporary_file:
                    temporary_path = Path(
                        temporary_file.name
                    )

                with zipfile.ZipFile(
                    temporary_path,
                    mode="w",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                ) as archive:

                    for entry in included:
                        pusinex = entry["pusinex"]

                        with pusinex.archivo.storage.open(
                            pusinex.archivo.name,
                            "rb",
                        ) as source_file:

                            archive.writestr(
                                entry["filename"],
                                source_file.read(),
                            )

                    archive.writestr(
                        MANIFEST_FILENAME,
                        build_manifest(
                            district["sections"]
                        ).encode("utf-8-sig"),
                    )

                temporary_path.replace(target_path)

            except Exception as exc:
                if (
                    temporary_path
                    and temporary_path.exists()
                ):
                    temporary_path.unlink()

                raise CommandError(
                    f"Error generando el paquete del "
                    f"Distrito {district_number:02d}: {exc}"
                ) from exc

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Generado: {target_path}"
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Paquetes VNM 2026 generados correctamente."
            )
        )
