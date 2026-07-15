from pypdf import PdfWriter

def unir_pdfs(lista_archivos, archivo_salida):
    # Inicializamos el "escritor" que funcionará como nuestro unificador
    merger = PdfWriter()

    try:
        # Recorremos la lista y agregamos cada PDF al final del documento
        for pdf in lista_archivos:
            merger.append(pdf)

        # Guardamos el resultado en el disco duro
        merger.write(archivo_salida)
        print(f"✅ ¡Éxito! Archivo unificado guardado como: {archivo_salida}")
        
    except Exception as e:
        print(f"❌ Ocurrió un error al unir los PDFs: {str(e)}")
        
    finally:
        # Siempre es buena práctica cerrar el documento para liberar memoria
        merger.close()

# USO DEL SCRIPT:
# Asegúrate de poner las rutas correctas a tus 3 archivos
archivos_a_unir = [
    "parte_1.pdf", 
    "parte_2.pdf", 
    "parte_3.pdf"
]

# Mandamos llamar la función
unir_pdfs(archivos_a_unir, "expediente_completo.pdf")