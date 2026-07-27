import os
import glob
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from apps.pusinex.models import Seccion, Municipio, Distrito, Entidad, Manzana


class Command(BaseCommand):
    help = "Une CSVs de manzanas, limpia la BD, inyecta registros y precalcula PE y LN en cascada."

    def add_arguments(self, parser):
        parser.add_argument(
            "ruta_directorio", type=str, help="Ruta a la carpeta con los archivos CSV"
        )

    def handle(self, *args, **kwargs):
        ruta = kwargs["ruta_directorio"]

        if not os.path.isdir(ruta):
            self.stdout.write(
                self.style.ERROR(f"Error: El directorio {ruta} no existe.")
            )
            return

        archivos_csv = glob.glob(os.path.join(ruta, "*.csv"))
        if not archivos_csv:
            self.stdout.write(
                self.style.WARNING(f"No se encontraron archivos CSV en {ruta}.")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Detectados {len(archivos_csv)} archivos. Preparando carga masiva..."
            )
        )
        manzanas_a_crear = []
        LOTE_SIZE = 5000
        contador_total = 0

        try:
            with transaction.atomic():
                Manzana.objects.all().delete()

                for archivo in archivos_csv:
                    self.stdout.write(
                        self.style.NOTICE(f"Procesando: {os.path.basename(archivo)}")
                    )
                    with open(archivo, mode="r", encoding="utf-8-sig") as f:
                        reader = csv.reader(f)
                        next(reader, None)

                        for row in reader:
                            if not row or len(row) < 8:
                                continue

                            manzanas_a_crear.append(
                                Manzana(
                                    seccion_id=int(row[3]),
                                    localidad=int(row[4]),
                                    manzana=int(row[5]),
                                    padron=int(row[6]),
                                    lista_nominal=int(row[7]),
                                )
                            )
                            contador_total += 1

                            if len(manzanas_a_crear) >= LOTE_SIZE:
                                Manzana.objects.bulk_create(manzanas_a_crear)
                                self.stdout.write(
                                    f"   ... {contador_total} manzanas..."
                                )
                                manzanas_a_crear = []

                if manzanas_a_crear:
                    Manzana.objects.bulk_create(manzanas_a_crear)
                    self.stdout.write(
                        f"   ... {contador_total} manzanas (Buffer final)..."
                    )

                self.stdout.write(
                    self.style.SUCCESS("Inyección de manzanas terminada.")
                )
                self.stdout.write(
                    self.style.WARNING(
                        "\nIniciando precomputación jerárquica de PE y LN..."
                    )
                )

                # 1. Secciones (Agregan padron y lista_nominal desde Manzana)
                totales_secciones = Manzana.objects.values("seccion_id").annotate(
                    p_sum=Sum("padron"), ln_sum=Sum("lista_nominal")
                )
                secciones_dict = {x["seccion_id"]: x for x in totales_secciones}
                secciones_a_actualizar = []
                for sec in Seccion.objects.all():
                    datos = secciones_dict.get(sec.seccion)
                    sec.pe = datos["p_sum"] if datos else 0
                    sec.ln = datos["ln_sum"] if datos else 0
                    secciones_a_actualizar.append(sec)
                Seccion.objects.bulk_update(secciones_a_actualizar, ["pe", "ln"])
                self.stdout.write("   ✔ Secciones actualizadas.")

                # 2. Municipios (Agregan pe y ln desde Seccion)
                totales_municipios = Seccion.objects.values("municipio_id").annotate(
                    p_sum=Sum("pe"), ln_sum=Sum("ln")
                )
                mun_dict = {x["municipio_id"]: x for x in totales_municipios}
                municipios_a_actualizar = []
                for mun in Municipio.objects.all():
                    datos = mun_dict.get(mun.municipio)
                    mun.pe = datos["p_sum"] if datos else 0
                    mun.ln = datos["ln_sum"] if datos else 0
                    municipios_a_actualizar.append(mun)
                Municipio.objects.bulk_update(municipios_a_actualizar, ["pe", "ln"])
                self.stdout.write("   ✔ Municipios actualizados.")

                # 3. Distritos (Agregan pe y ln desde Seccion)
                totales_distritos = Seccion.objects.values("distrito_id").annotate(
                    p_sum=Sum("pe"), ln_sum=Sum("ln")
                )
                dist_dict = {x["distrito_id"]: x for x in totales_distritos}
                distritos_a_actualizar = []
                for dist in Distrito.objects.all():
                    datos = dist_dict.get(dist.distrito)
                    dist.pe = datos["p_sum"] if datos else 0
                    dist.ln = datos["ln_sum"] if datos else 0
                    distritos_a_actualizar.append(dist)
                Distrito.objects.bulk_update(distritos_a_actualizar, ["pe", "ln"])
                self.stdout.write("   ✔ Distritos actualizados.")

                # 4. Entidades (Agregan pe y ln desde Distrito)
                totales_entidades = Distrito.objects.values("entidad_id").annotate(
                    p_sum=Sum("pe"), ln_sum=Sum("ln")
                )
                ent_dict = {x["entidad_id"]: x for x in totales_entidades}
                entidades_a_actualizar = []
                for ent in Entidad.objects.all():
                    datos = ent_dict.get(ent.entidad)
                    ent.pe = datos["p_sum"] if datos else 0
                    ent.ln = datos["ln_sum"] if datos else 0
                    entidades_a_actualizar.append(ent)
                Entidad.objects.bulk_update(entidades_a_actualizar, ["pe", "ln"])
                self.stdout.write("   ✔ Entidades actualizadas.")

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nProceso concluido. {contador_total} registros procesados."
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\nError crítico. Transacción abortada: {str(e)}")
            )
