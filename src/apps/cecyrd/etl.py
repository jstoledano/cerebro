import csv
import zipfile
import os
import tempfile
import threading
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone
from apps.cecyrd.models import Tramite

BATCH_SIZE = 1000


def convertir_fecha_para_db(fecha_str):
    """Limpia y convierte la fecha de texto al timezone configurado en Django."""
    if not fecha_str or fecha_str.strip() == "":
        return None

    # Si solo viene la fecha (10 caracteres), le agregamos una hora base
    if len(fecha_str.strip()) <= 10:
        fecha_str = fecha_str.strip() + " 00:00:00 AM"

    try:
        # Normalizamos los "a. m." / "p. m." que suele arrojar Excel o SQL
        fecha_limpia = fecha_str.replace("a. m.", "AM").replace("p. m.", "PM").strip()
        dt_naive = datetime.strptime(fecha_limpia, "%d/%m/%Y %I:%M:%S %p")
        return timezone.make_aware(dt_naive, timezone.get_default_timezone())
    except ValueError:
        return None


def calcular_intervalo(fecha_inicio_str, fecha_fin_str):
    """Calcula la diferencia exacta entre dos fechas."""
    start = convertir_fecha_para_db(fecha_inicio_str)
    end = convertir_fecha_para_db(fecha_fin_str)
    if start and end:
        delta = end - start
        # Manejo seguro por si hay fechas invertidas
        return timedelta(seconds=abs(int(delta.total_seconds())))
    return None


def registrar_progreso(task_id, status, progreso, msj=None, stats=None):
    """Escribe el avance en Redis/Memoria para que el navegador lo lea."""
    data = cache.get(
        task_id, {"status": "iniciando", "progress": 0, "logs": [], "stats": {}}
    )
    data["status"] = status
    data["progress"] = progreso
    if msj:
        data["logs"].append(msj)
    if stats:
        data["stats"] = stats
    cache.set(task_id, data, timeout=3600)


def procesar_archivo_background(task_id, file_path, is_zip, password):
    """El corazón del proceso. Corre en segundo plano sin bloquear el servidor."""
    try:
        registrar_progreso(task_id, "procesando", 5, "Iniciando motor ETL...")
        data_file_path = file_path

        # 1. Descompresión Segura
        if is_zip:
            registrar_progreso(
                task_id, "procesando", 10, "Archivo ZIP detectado. Descomprimiendo..."
            )
            temp_dir = os.path.dirname(file_path)
            try:
                with zipfile.ZipFile(file_path, "r") as zf:
                    if password:
                        zf.setpassword(password.encode("utf-8"))
                    archivos_validos = [
                        f
                        for f in zf.namelist()
                        if f.endswith(".txt") or f.endswith(".csv")
                    ]

                    if not archivos_validos:
                        raise ValueError(
                            "El archivo comprimido no contiene datos legibles (.txt o .csv)"
                        )

                    zf.extract(archivos_validos[0], temp_dir)
                    data_file_path = os.path.join(temp_dir, archivos_validos[0])
                    registrar_progreso(
                        task_id, "procesando", 20, f"Archivo descomprimido con éxito."
                    )
            except Exception as e:
                error_str = str(e)
                # Capturamos el error en inglés de clave incorrecta de Python
                if (
                    "Bad password" in error_str
                    or "password required" in error_str.lower()
                ):
                    mensaje_usuario = "La contraseña del archivo es incorrecta. Por favor, verifica que hayas seleccionado el archivo de clave correcto."
                else:
                    mensaje_usuario = f"El archivo comprimido está dañado o no se puede abrir. Detalle: {error_str}"

                registrar_progreso(task_id, "error", 0, mensaje_usuario)
                return

        # 2. Conteo de líneas para la barra de progreso
        registrar_progreso(
            task_id, "procesando", 25, "Analizando volumen de registros..."
        )
        with open(data_file_path, "r", encoding="utf-8-sig") as f:
            total_lines = sum(1 for _ in f) - 1  # Restamos la cabecera
        registrar_progreso(
            task_id, "procesando", 30, f"Objetivo: {total_lines} filas. Procesando..."
        )

        # AQUI ESTA LA MAGIA: Cambiamos de lista a Diccionario
        batch_dict = {}
        procesados = 0
        errores = 0

        update_fields = [f.name for f in Tramite._meta.fields if f.name != "folio"]

        # 3. Lectura e Inyección
        with open(data_file_path, "r", encoding="utf-8-sig") as f:
            lector = csv.reader(f, delimiter="|")
            next(lector, None)  # Saltamos cabecera rígidamente por índice

            for row in lector:
                if len(row) < 22:
                    continue  # Fila corrupta, saltamos

                try:
                    folio_val = row[0].strip()
                    distrito_val = (
                        int(folio_val[5])
                        if len(folio_val) > 5 and folio_val[5].isdigit()
                        else 0
                    )
                    mac_val = folio_val[2:8] if len(folio_val) > 7 else ""

                    tramite = Tramite(
                        folio=folio_val,
                        estatus=row[1],
                        causa_rechazo=row[2],
                        movimiento_solicitado=row[3],
                        movimiento_definitivo=row[4],
                        fecha_tramite=convertir_fecha_para_db(row[5]),
                        fecha_recibido_cecyrd=convertir_fecha_para_db(row[6]),
                        fecha_registrado_cecyrd=convertir_fecha_para_db(row[7]),
                        fecha_rechazado=convertir_fecha_para_db(row[8]),
                        fecha_cancelado_movimiento_posterior=convertir_fecha_para_db(
                            row[9]
                        ),
                        fecha_alta_pe=convertir_fecha_para_db(row[10]),
                        fecha_afectacion_padron=convertir_fecha_para_db(row[11]),
                        fecha_actualizacion_pe=convertir_fecha_para_db(row[12]),
                        fecha_reincorporacion_pe=convertir_fecha_para_db(row[13]),
                        fecha_exitoso=convertir_fecha_para_db(row[14]),
                        fecha_lote_produccion=convertir_fecha_para_db(row[15]),
                        fecha_listo_reimpresion=convertir_fecha_para_db(row[16]),
                        fecha_cpv_creada=convertir_fecha_para_db(row[17]),
                        fecha_cpv_registrada_mac=convertir_fecha_para_db(row[18]),
                        fecha_cpv_disponible=convertir_fecha_para_db(row[19]),
                        fecha_cpv_entregada=convertir_fecha_para_db(row[20]),
                        fecha_afectacion_ln=convertir_fecha_para_db(row[21]),
                        distrito=distrito_val,
                        mac=mac_val,
                        tramo_disponible=calcular_intervalo(row[5], row[19]),
                        tramo_entrega=calcular_intervalo(row[19], row[20]),
                        tramo_exitoso=calcular_intervalo(row[5], row[14]),
                    )
                    # Almacenamos en el diccionario. Si el folio ya existe en este lote de 1000, se sobrescribe solo.
                    batch_dict[folio_val] = tramite
                except Exception:
                    errores += 1

                # Inserción en bloques evaluando la longitud del diccionario
                if len(batch_dict) >= BATCH_SIZE:
                    # Usamos .values() para extraer la lista final sin duplicados
                    Tramite.objects.bulk_create(
                        batch_dict.values(),
                        update_conflicts=True,
                        unique_fields=["folio"],
                        update_fields=update_fields,
                    )
                    procesados += len(batch_dict)
                    porcentaje = (
                        30 + int((procesados / total_lines) * 65)
                        if total_lines > 0
                        else 90
                    )
                    registrar_progreso(
                        task_id,
                        "procesando",
                        porcentaje,
                        f"Upsert aplicado: {procesados}/{total_lines} trámites...",
                    )
                    batch_dict = {}  # Limpiamos el diccionario

            # Inyectar el remanente del bloque final
            if batch_dict:
                Tramite.objects.bulk_create(
                    batch_dict.values(),
                    update_conflicts=True,
                    unique_fields=["folio"],
                    update_fields=update_fields,
                )
                procesados += len(batch_dict)

        # 4. Limpieza del servidor
        if os.path.exists(file_path):
            os.remove(file_path)
        if is_zip and os.path.exists(data_file_path):
            os.remove(data_file_path)

        stats = {"total": total_lines, "procesados": procesados, "errores": errores}
        registrar_progreso(
            task_id,
            "completado",
            100,
            f"✅ Base de datos sincronizada correctamente.",
            stats,
        )

    except Exception as e:
        registrar_progreso(
            task_id, "error", 0, f"Error crítico durante el proceso: {str(e)}"
        )

def iniciar_etl_thread(file_obj, is_zip, key_file_obj=None):
    """Guarda el archivo en memoria temporal y lanza el proceso paralelo."""
    import uuid

    task_id = str(uuid.uuid4())

    password = None
    if key_file_obj:
        password = key_file_obj.read().decode("utf-8").strip()

    # Guardar archivo en disco temporal (Alivia la RAM)
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"cecyrd_{task_id}_{file_obj.name}")
    with open(file_path, "wb+") as dest:
        for chunk in file_obj.chunks():
            dest.write(chunk)

    thread = threading.Thread(
        target=procesar_archivo_background, args=(task_id, file_path, is_zip, password)
    )
    thread.daemon = True
    thread.start()

    return task_id
