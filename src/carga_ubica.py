import os
import csv
from apps.pusinex.models import Seccion

carpeta_base = r"C:\Users\javier.sanchezt\Projects\cerebro\data"
archivos_csv = ["td1.csv", "td2.csv", "td3.csv"]
total_actualizadas = 0

print("--- INICIANDO CARGA POR ÍNDICES ---")

# Cargamos los IDs de la BD a la memoria
secciones_en_bd = set(Seccion.objects.values_list('seccion', flat=True))
print(f"📊 Secciones actualmente en la Base de Datos: {len(secciones_en_bd)}")

if len(secciones_en_bd) == 0:
    print("⚠️ ALERTA: Tu base de datos no tiene secciones. ¡Por eso no se actualiza nada!")
else:
    for nombre_archivo in archivos_csv:
        ruta_completa = os.path.join(carpeta_base, nombre_archivo)
        
        if not os.path.exists(ruta_completa):
            print(f"⚠️ No encontrado: {ruta_completa}")
            continue
            
        print(f"\nProcesando {nombre_archivo}...")
        
        with open(ruta_completa, mode='r', encoding='utf-8-sig') as archivo:
            lector = csv.reader(archivo)
            next(lector, None) # Saltamos cabecera
            
            contador = 0
            for i, fila in enumerate(lector):
                if len(fila) < 2 or not fila[0].strip():
                    continue
                    
                try:
                    seccion_id = int(fila[0].strip())
                except ValueError:
                    continue 
                    
                ubica_val = fila[1].strip() if len(fila) > 1 else ""
                
                distancia_val = None
                if len(fila) > 2 and fila[2].strip():
                    try:
                        distancia_val = int(fila[2].strip())
                    except ValueError:
                        pass
                        
                traslado_val = None
                if len(fila) > 3 and fila[3].strip():
                    try:
                        traslado_val = int(fila[3].strip())
                    except ValueError:
                        pass

                # Diagnóstico de la primera fila leída
                if i == 0:
                    print(f"   🔍 Muestra Fila 1 -> ID CSV: {seccion_id} | Existe en BD: {seccion_id in secciones_en_bd}")

                if seccion_id in secciones_en_bd:
                    Seccion.objects.filter(seccion=seccion_id).update(
                        ubica=ubica_val,
                        distancia=distancia_val,
                        traslado=traslado_val
                    )
                    contador += 1

            print(f"✔️ {nombre_archivo}: {contador} registros cruzados y actualizados.")
            total_actualizadas += contador

    print("-" * 30)
    print(f"🚀 PROCESO FINALIZADO. Total general actualizado: {total_actualizadas}")