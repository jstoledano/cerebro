import getpass
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone

from apps.pusinex.mge.doctor import (
    revisar_entidad,
    revisar_distrito,
    revisar_distrito_local,
    revisar_municipio,
    revisar_seccion,
    revisar_manzana,
)
from apps.pusinex.mge.entidad import (
    actualizar_entidad,
)
from apps.pusinex.mge.distrito import (
    actualizar_distrito,
)
from apps.pusinex.mge.distrito_local import (
    actualizar_distrito_local,
)
from apps.pusinex.mge.municipio import (
    actualizar_municipio,
)
from apps.pusinex.mge.seccion import (
    actualizar_seccion,
)
from apps.pusinex.mge.manzana import (
    actualizar_manzana,
)
from apps.pusinex.models import ActualizacionMGE


class Command(BaseCommand):
    help = (
        "Actualiza el Marco Geográfico Electoral "
        "desde la BGD."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "ruta_bged",
            type=str,
            help=(
                "Ruta al directorio raíz "
                "de la BGD."
            ),
        )

        parser.add_argument(
            "--doctor",
            action="store_true",
            help=(
                "Valida archivos y condiciones "
                "necesarias sin modificar "
                "la base de datos."
            ),
        )

    def handle(self, *args, **options):
        ruta = (
            Path(options["ruta_bged"])
            .expanduser()
            .resolve()
        )

        solo_doctor = options["doctor"]
        actor = getpass.getuser()

        tipo = (
            "DOCTOR"
            if solo_doctor
            else "ACTUALIZACION"
        )

        ejecucion = ActualizacionMGE.objects.create(
            tipo=tipo,
            estado="INICIADA",
            actor=actor,
            origen=str(ruta),
        )

        try:
            # ---------------------------------
            # DOCTOR
            # ---------------------------------

            self.stdout.write("")
            self.stdout.write(
                self.style.NOTICE(
                    "Diagnóstico del "
                    "Marco Geográfico Electoral"
                )
            )

            diagnosticos = {
                "entidad":
                    revisar_entidad(ruta),
                "distrito":
                    revisar_distrito(ruta),
                "distrito_local":
                    revisar_distrito_local(ruta),
                "municipio":
                    revisar_municipio(ruta),
                "seccion":
                    revisar_seccion(ruta),
                "manzana":
                    revisar_manzana(ruta),
            }

            self._mostrar_diagnosticos(
                diagnosticos
            )

            apto = all(
                diagnostico["apto"]
                for diagnostico
                in diagnosticos.values()
            )

            # ---------------------------------
            # BGD NO APTA
            # ---------------------------------

            if not apto:
                errores = []

                for diagnostico in (
                    diagnosticos.values()
                ):
                    errores.extend(
                        diagnostico["errores"]
                    )

                ejecucion.estado = "NO_APTO"
                ejecucion.fin = timezone.now()
                ejecucion.reporte = {
                    "doctor": diagnosticos,
                }
                ejecucion.mensaje_error = (
                    "\n".join(errores)
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
                        "La BGD no está en "
                        "condiciones de ser "
                        "actualizada."
                    )
                )

                return

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Diagnóstico satisfactorio."
                )
            )

            # ---------------------------------
            # SOLO DOCTOR
            # ---------------------------------

            if solo_doctor:
                ejecucion.estado = "APTO"
                ejecucion.fin = timezone.now()
                ejecucion.reporte = {
                    "doctor": diagnosticos,
                }

                ejecucion.save(
                    update_fields=[
                        "estado",
                        "fin",
                        "reporte",
                    ]
                )

                return

            resultados = {}

            # ---------------------------------
            # ENTIDAD
            # ---------------------------------

            self.stdout.write("")
            self.stdout.write(
                "Actualizando Entidad..."
            )

            resultados["entidad"] = (
                actualizar_entidad(ruta)
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Entidad actualizada "
                    "correctamente."
                )
            )

            # ---------------------------------
            # DISTRITO
            # ---------------------------------

            self.stdout.write("")
            self.stdout.write(
                "Actualizando Distrito..."
            )

            resultados["distrito"] = (
                actualizar_distrito(
                    ruta,
                    ejecucion,
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Distrito actualizado "
                    "correctamente."
                )
            )

            # ---------------------------------
            # DISTRITO LOCAL
            # ---------------------------------

            self.stdout.write("")
            self.stdout.write(
                "Actualizando Distrito Local..."
            )

            resultados["distrito_local"] = (
                actualizar_distrito_local(
                    ruta,
                    ejecucion,
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Distrito Local actualizado "
                    "correctamente."
                )
            )

            # ---------------------------------
            # MUNICIPIO
            # ---------------------------------

            self.stdout.write("")
            self.stdout.write(
                "Actualizando Municipio..."
            )

            resultados["municipio"] = (
                actualizar_municipio(
                    ruta,
                    ejecucion,
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Municipio actualizado "
                    "correctamente."
                )
            )

            # ---------------------------------
            # SECCIÓN
            # ---------------------------------

            self.stdout.write("")
            self.stdout.write(
                "Actualizando Sección..."
            )

            resultados["seccion"] = (
                actualizar_seccion(
                    ruta,
                    ejecucion,
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Sección actualizada "
                    "correctamente."
                )
            )

            # ---------------------------------
            # MANZANA
            # ---------------------------------

            self.stdout.write("")
            self.stdout.write(
                "Actualizando Manzana..."
            )

            resultados["manzana"] = (
                actualizar_manzana(ruta)
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Manzana actualizada "
                    "correctamente."
                )
            )

            # ---------------------------------
            # FINALIZAR EJECUCIÓN
            # ---------------------------------

            ejecucion.estado = "COMPLETADA"
            ejecucion.fin = timezone.now()
            ejecucion.reporte = {
                "doctor": diagnosticos,
                "capas": resultados,
            }

            ejecucion.save(
                update_fields=[
                    "estado",
                    "fin",
                    "reporte",
                ]
            )

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Marco Geográfico Electoral "
                    "actualizado correctamente."
                )
            )

            self._mostrar_resultados(
                resultados
            )

        # ---------------------------------
        # ERROR
        # ---------------------------------

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

    def _mostrar_diagnosticos(
        self,
        diagnosticos,
    ):
        # ---------------------------------
        # MOSTRAR DOCTOR
        # ---------------------------------

        for nombre_capa, diagnostico in (
            diagnosticos.items()
        ):
            self.stdout.write("")

            self.stdout.write(
                self.style.NOTICE(
                    f"Capa: {nombre_capa}"
                )
            )

            for prueba in (
                diagnostico[
                    "comprobaciones"
                ]
            ):
                simbolo = (
                    "OK"
                    if prueba["ok"]
                    else "ERROR"
                )

                linea = (
                    f"[{simbolo}] "
                    f"{prueba['prueba']}: "
                    f"{prueba['detalle']}"
                )

                if prueba["ok"]:
                    self.stdout.write(
                        self.style.SUCCESS(
                            linea
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            linea
                        )
                    )

            if diagnostico["errores"]:
                self.stdout.write("")

                for error in (
                    diagnostico["errores"]
                ):
                    self.stdout.write(
                        self.style.ERROR(
                            f"  - {error}"
                        )
                    )

    def _mostrar_resultados(
        self,
        resultados,
    ):
        # ---------------------------------
        # MOSTRAR RESULTADOS
        # ---------------------------------

        for nombre_capa, resultado in (
            resultados.items()
        ):
            self.stdout.write("")

            nombre = (
                nombre_capa
                .replace("_", " ")
                .title()
            )

            self.stdout.write(
                self.style.NOTICE(nombre)
            )

            insertados = resultado.get(
                "insertados",
                0,
            )

            actualizados = resultado.get(
                "actualizados",
                0,
            )

            eliminados = resultado.get(
                "eliminados",
                0,
            )

            sin_cambios = resultado.get(
                "sin_cambios",
                0,
            )

            reactivados = resultado.get(
                "reactivados",
                0,
            )

            desactivados = resultado.get(
                "desactivados",
                0,
            )

            cambios_registrados = resultado.get(
                "cambios_registrados",
                0,
            )

            self.stdout.write(
                f"  Insertados: {insertados}"
            )

            self.stdout.write(
                f"  Actualizados: {actualizados}"
            )

            if eliminados:
                self.stdout.write(
                    f"  Eliminados: {eliminados}"
                )

            self.stdout.write(
                f"  Sin cambios: {sin_cambios}"
            )

            if reactivados:
                self.stdout.write(
                    f"  Reactivados: {reactivados}"
                )

            if desactivados:
                self.stdout.write(
                    f"  Desactivados: {desactivados}"
                )

            if cambios_registrados:
                self.stdout.write(
                    "  Cambios MGE registrados: "
                    f"{cambios_registrados}"
                )

            campos_modificados = resultado.get(
                "campos_modificados"
            )

            if campos_modificados:
                self.stdout.write(
                    "  Campos modificados: "
                    f"{campos_modificados}"
                )
