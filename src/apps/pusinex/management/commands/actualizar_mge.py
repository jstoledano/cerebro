import getpass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.pusinex.mge.doctor import revisar_entidad
from apps.pusinex.mge.entidad import actualizar_entidad
from apps.pusinex.models import ActualizacionMGE


class Command(BaseCommand):
    help = "Actualiza el Marco Geográfico Electoral desde la BGD."

    def add_arguments(self, parser):
        parser.add_argument(
            "ruta_bged",
            type=str,
            help="Ruta al directorio raíz de la BGD.",
        )

        parser.add_argument(
            "--doctor",
            action="store_true",
            help="Valida archivos y condiciones sin actualizar la base de datos.",
        )

    def handle(self, *args, **options):
        ruta = Path(options["ruta_bged"])
        solo_doctor = options["doctor"]
        actor = getpass.getuser()

        tipo = "DOCTOR" if solo_doctor else "ACTUALIZACION"

        ejecucion = ActualizacionMGE.objects.create(
            tipo=tipo,
            estado="INICIADA",
            actor=actor,
            origen=str(ruta),
        )

        try:
            self.stdout.write("")
            self.stdout.write(
                self.style.NOTICE(
                    "Diagnóstico del Marco Geográfico Electoral"
                )
            )
            self.stdout.write("")

            diagnostico = revisar_entidad(ruta)

            for prueba in diagnostico["comprobaciones"]:
                simbolo = "OK" if prueba["ok"] else "ERROR"

                linea = (
                    f"[{simbolo}] "
                    f"{prueba['prueba']}: "
                    f"{prueba['detalle']}"
                )

                if prueba["ok"]:
                    self.stdout.write(
                        self.style.SUCCESS(linea)
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(linea)
                    )

            if not diagnostico["apto"]:
                ejecucion.estado = "NO_APTO"
                ejecucion.fin = timezone.now()
                ejecucion.reporte = {
                    "doctor": diagnostico,
                }
                ejecucion.mensaje_error = "\n".join(
                    diagnostico["errores"]
                )

                ejecucion.save(
                    update_fields=[
                        "estado",
                        "fin",
                        "reporte",
                        "mensaje_error",
                    ]
                )

                self.stdout.write("")
                self.stdout.write(
                    self.style.ERROR(
                        "La BGD no está en condiciones de ser actualizada."
                    )
                )

                return

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Diagnóstico satisfactorio."
                )
            )

            if solo_doctor:
                ejecucion.estado = "APTO"
                ejecucion.fin = timezone.now()
                ejecucion.reporte = {
                    "doctor": diagnostico,
                }

                ejecucion.save(
                    update_fields=[
                        "estado",
                        "fin",
                        "reporte",
                    ]
                )

                return

            self.stdout.write("")
            self.stdout.write(
                "Actualizando Entidad..."
            )

            resultado = actualizar_entidad(ruta)

            ejecucion.estado = "COMPLETADA"
            ejecucion.fin = timezone.now()
            ejecucion.reporte = {
                "doctor": diagnostico,
                "capas": {
                    "entidad": resultado,
                },
            }

            ejecucion.save(
                update_fields=[
                    "estado",
                    "fin",
                    "reporte",
                ]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Entidad actualizada correctamente."
                )
            )

            self.stdout.write(
                f"Insertados: {resultado['insertados']}"
            )
            self.stdout.write(
                f"Actualizados: {resultado['actualizados']}"
            )
            self.stdout.write(
                f"Sin cambios: {resultado['sin_cambios']}"
            )

        except Exception as exc:
            ejecucion.estado = "ERROR"
            ejecucion.fin = timezone.now()
            ejecucion.mensaje_error = str(exc)

            ejecucion.save(
                update_fields=[
                    "estado",
                    "fin",
                    "mensaje_error",
                ]
            )

            raise CommandError(str(exc))
