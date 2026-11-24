"""Importar asignaciones informativas de ZORE/ARE desde uno o varios distritos.

CSV UTF-8 con encabezados seccion,zore,are,casillas_ln.
El distrito se deduce de Seccion.distrito y se conserva como clave interna.
La sustitucion es atomica por los distritos presentes en el archivo.
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.pusinex.models import Distrito, Seccion
from apps.pusinex.zore_models import Are, SeccionAre, Zore

REQUIRED = {"seccion", "zore", "are"}
OPTIONAL = {"casillas_ln"}


def entero(valor, campo, linea, requerido=True):
    texto = (valor or "").strip()
    if not texto and not requerido:
        return None
    if not texto or not texto.isdigit() or int(texto) < 1:
        raise CommandError(f"Linea {linea}: {campo} debe ser entero positivo")
    return int(texto)


def leer_csv(ruta):
    try:
        with ruta.open("r", encoding="utf-8-sig", newline="") as file:
            primera = file.readline()
            file.seek(0)
            delimitador = ";" if primera.count(";") > primera.count(",") else ","
            reader = csv.DictReader(file, delimiter=delimitador, skipinitialspace=True)
            if not reader.fieldnames:
                raise CommandError("CSV vacio o sin encabezados")
            encabezados = {h.strip().lower() for h in reader.fieldnames if h}
            faltan = REQUIRED - encabezados
            sobran = encabezados - REQUIRED - OPTIONAL
            if faltan or sobran:
                raise CommandError(
                    f"Encabezados incorrectos. Faltan: {sorted(faltan)}; "
                    f"desconocidos: {sorted(sobran)}"
                )
            filas = []
            for linea, raw in enumerate(reader, start=2):
                if None in raw:
                    raise CommandError(f"Linea {linea}: columnas adicionales")
                datos = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
                if not any(datos.values()):
                    continue
                filas.append({
                    "linea": linea,
                    "seccion": entero(datos.get("seccion"), "seccion", linea),
                    "zore": entero(datos.get("zore"), "zore", linea),
                    "are": entero(datos.get("are"), "are", linea),
                    "casillas_ln": entero(datos.get("casillas_ln"), "casillas_ln", linea, requerido=False),
                })
    except (OSError, UnicodeError) as exc:
        raise CommandError(f"No se pudo leer el CSV: {exc}") from exc
    if not filas:
        raise CommandError("El CSV no contiene asignaciones")
    return filas


def verificar(filas, secciones_db, distritos_db, permitir_incompleto=False):
    """Verifica las asignaciones tras resolver el distrito por seccion."""
    errores = []
    por_seccion = defaultdict(list)
    zona_por_are = {}
    vistos = set()
    for fila in filas:
        d, sec, z, a = (fila[x] for x in ("distrito", "seccion", "zore", "are"))
        ds = (d, sec)
        if (sec, a) in vistos:
            errores.append(f"Linea {fila['linea']}: ARE {a} repetida en seccion {sec:04}")
        vistos.add((sec, a))
        por_seccion[ds].append(fila)
        if d not in distritos_db:
            errores.append(f"Linea {fila['linea']}: distrito {d:02} inexistente")
        if ds not in secciones_db:
            errores.append(f"Linea {fila['linea']}: seccion {sec:04} inactiva en distrito {d:02}")
        clave_are = (d, a)
        if clave_are in zona_por_are and zona_por_are[clave_are] != z:
            errores.append(f"Linea {fila['linea']}: ARE {a} asignada a dos ZORE distintas")
        zona_por_are[clave_are] = z
    for ds, partes in por_seccion.items():
        if len(partes) > 2:
            errores.append(f"Distrito {ds[0]:02}, seccion {ds[1]:04}: mas de dos ARE")
        if len({f['zore'] for f in partes}) != 1:
            errores.append(f"Distrito {ds[0]:02}, seccion {ds[1]:04}: dos ZORE diferentes")
        if len(partes) == 2 and any(f['casillas_ln'] is None for f in partes):
            errores.append(f"Distrito {ds[0]:02}, seccion {ds[1]:04}: falta casillas_ln para una ARE compartida")
    if not permitir_incompleto:
        presentes = set(por_seccion)
        pendientes = set(secciones_db) - presentes
        if pendientes:
            muestra = ", ".join(f"{d:02}/{sec:04}" for d, sec in sorted(pendientes)[:15])
            errores.append(
                f"Asignacion distrital incompleta: {len(pendientes)} secciones activas sin ARE. "
                f"Primeras: {muestra}"
            )
    return errores, por_seccion, zona_por_are


class Command(BaseCommand):
    help = "Carga CSV informativo de ZORE y ARE, con reemplazo distrital atomico"

    def add_arguments(self, parser):
        parser.add_argument("archivo", type=Path, help="CSV de uno o varios distritos")
        parser.add_argument("--simular", action="store_true", help="Validar y mostrar resumen sin escribir")
        parser.add_argument(
            "--permitir-incompleto", action="store_true",
            help="Admitir temporalmente secciones sin asignacion (uso de pruebas)",
        )

    def handle(self, *args, **options):
        filas = leer_csv(options["archivo"])
        # Seccion.seccion es PK global en el MGE actual de PUSINEX.
        numeros = {fila["seccion"] for fila in filas}
        ubicaciones = dict(
            Seccion.objects.filter(pk__in=numeros).values_list("seccion", "distrito_id")
        )
        ausentes = sorted(numeros - set(ubicaciones))
        if ausentes:
            muestra = ", ".join(f"{sec:04}" for sec in ausentes[:20])
            raise CommandError(
                f"Secciones inexistentes en el MGE: {muestra}. No se realizaron cambios"
            )
        for fila in filas:
            fila["distrito"] = ubicaciones[fila["seccion"]]
        distritos = sorted({fila["distrito"] for fila in filas})
        distritos_db = set(Distrito.objects.filter(pk__in=distritos).values_list("pk", flat=True))
        secciones_db = set(
            Seccion.objects.filter(distrito_id__in=distritos, activa=True)
            .values_list("distrito_id", "seccion")
        )
        errores, por_seccion, zona_por_are = verificar(
            filas, secciones_db, distritos_db,
            permitir_incompleto=options["permitir_incompleto"],
        )
        if errores:
            for error in errores[:40]:
                self.stderr.write(error)
            raise CommandError(f"CSV rechazado: {len(errores)} error(es). No se realizaron cambios")
        zonas = {(f["distrito"], f["zore"]) for f in filas}
        total_compartidas = sum(len(x) == 2 for x in por_seccion.values())
        self.stdout.write(
            f"Distritos {', '.join(f'{d:02}' for d in distritos)}; "
            f"ZORE {len(zonas)}; ARE {len(zona_por_are)}; "
            f"secciones {len(por_seccion)}; compartidas {total_compartidas}; "
            f"relaciones {len(filas)}"
        )
        if options["simular"]:
            self.stdout.write(self.style.SUCCESS("Simulacion correcta; base de datos sin cambios"))
            return
        with transaction.atomic():
            # Serializa sustituciones simultaneas del mismo distrito.
            list(Distrito.objects.select_for_update().filter(pk__in=distritos))
            datos_z = {
                (z.distrito_id, z.numero): (z.supervisor_nombre, z.supervisor_correo, z.supervisor_telefono)
                for z in Zore.objects.filter(distrito_id__in=distritos)
            }
            datos_a = {
                (a.distrito_id, a.numero): (a.cae_nombre, a.cae_correo, a.cae_telefono)
                for a in Are.objects.filter(distrito_id__in=distritos)
            }
            Zore.objects.filter(distrito_id__in=distritos).delete()
            zore_objs = {}
            for d, numero in sorted(zonas):
                nombre, correo, telefono = datos_z.get((d, numero), ("", "", ""))
                zore_objs[(d, numero)] = Zore.objects.create(
                    distrito_id=d, numero=numero,
                    supervisor_nombre=nombre, supervisor_correo=correo,
                    supervisor_telefono=telefono,
                )
            are_objs = {}
            for (d, numero), z in sorted(zona_por_are.items()):
                nombre, correo, telefono = datos_a.get((d, numero), ("", "", ""))
                are_objs[(d, numero)] = Are.objects.create(
                    distrito_id=d, numero=numero, zore=zore_objs[(d, z)],
                    cae_nombre=nombre, cae_correo=correo, cae_telefono=telefono,
                )
            SeccionAre.objects.bulk_create([
                SeccionAre(
                    seccion_id=f["seccion"],
                    are=are_objs[(f["distrito"], f["are"])],
                    casillas_ln=f["casillas_ln"],
                )
                for f in filas
            ], batch_size=500)
        self.stdout.write(self.style.SUCCESS("Asignaciones reemplazadas correctamente"))
