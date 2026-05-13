import hashlib
import json
import os
import shutil
import tempfile
import time
import zipfile
import glob
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from apps.docs.models import Documento


class Command(BaseCommand):
    help = "Genera el paquete CMI Portátil (ZIP) con autoverificación y vigencia."

    def handle(self, *args, **options):
        start_time = time.time()

        # Configuración de Fechas
        build_date = timezone.now()
        expiration_date = build_date + timedelta(days=15)

        # 1. Configuración de Directorios
        base_temp_dir = tempfile.gettempdir()
        cmi_build_dir = os.path.join(base_temp_dir, "cmi_build")
        docs_dir = os.path.join(cmi_build_dir, "docs")
        assets_dir = os.path.join(cmi_build_dir, "assets")

        if os.path.exists(cmi_build_dir):
            shutil.rmtree(cmi_build_dir)
        os.makedirs(docs_dir)
        os.makedirs(assets_dir)

        # 1.1 Copiar Assets (GIFs y Librerías Static)
        # Asumiendo estructura src/apps/docs/static/docs/images/
        static_docs_dir = settings.APPS_DIR / "docs" / "static" / "docs"
        source_img_dir = static_docs_dir / "images"
        source_css_dir = static_docs_dir / "css"
        source_js_dir = static_docs_dir / "js"

        # Copiar GIFs y Logo

        assets_to_copy = ["scanning.gif", "fingerprint.gif", "ok.gif", "logo.svg"]

        for asset in assets_to_copy:
            # Intentar primero en docs/static/img
            src_asset = os.path.join(source_img_dir, asset)

            if os.path.exists(src_asset):
                shutil.copy2(src_asset, os.path.join(assets_dir, asset))
            else:
                self.stdout.write(
                    self.style.WARNING(f"Asset no encontrado: {src_asset}")
                )

        # Copiar Librerías (DaisyUI, Tailwind)
        assets_map = {
            "daisyui.min.css": source_css_dir,
            "tailwind.min.js": source_js_dir,
        }

        for filename, source_dir in assets_map.items():
            src_path = os.path.join(source_dir, filename)
            if os.path.exists(src_path):
                shutil.copy2(src_path, os.path.join(assets_dir, filename))
            else:
                self.stdout.write(self.style.WARNING(f"Lib no encontrada: {src_path}"))

        # 2. Recolección de Documentos
        # 2. Recolección de Documentos
        active_docs = (
            Documento.objects.filter(activo=True)
            .select_related("proceso", "tipo")
            .prefetch_related("revision_set")
        )
        manifest = {}
        errors = 0

        self.stdout.write(f"Procesando {active_docs.count()} documentos...")

        for doc in active_docs:
            rev = doc.latest_revision
            if not rev or not rev.archivo:
                continue

            # Definir rutas
            tipo_slug = doc.tipo.slug
            filename = os.path.basename(rev.archivo.name)
            rel_path = f"docs/{tipo_slug}/{filename}"
            dest_path = os.path.join(cmi_build_dir, rel_path)

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # 2.1 Copiar archivo
            try:
                shutil.copy2(rev.archivo.path, dest_path)
            except FileNotFoundError:
                self.stdout.write(
                    self.style.ERROR(f"Archivo no encontrado: {rev.archivo.path}")
                )
                errors += 1
                continue

            # 2.2 Calcular Hash Real (Validación)
            with open(dest_path, "rb") as f:
                sha256 = hashlib.sha256()
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
                file_hash = sha256.hexdigest()

            # 2.3 Agregar al manifiesto
            manifest[rel_path] = {
                "hash": file_hash,
                "size": rev.archivo.size,
                "nombre": doc.nombre,
                "proceso": doc.proceso.proceso if doc.proceso else "General",
                "tipo": doc.tipo.tipo,
            }

            # Validación opcional contra DB (si existiera campo hash confiable)
            if rev.checksum and file_hash != rev.checksum:
                self.stdout.write(
                    self.style.WARNING(f"Mismatch hash DB vs File: {rel_path}")
                )

        # 3. Renderizar index.html desde Template
        context = {
            "build_date": build_date,
            "expiration_date": expiration_date,
        }
        index_content = render_to_string("docs/portable_index.html", context)
        index_path = os.path.join(cmi_build_dir, "index.html")

        # Escribir con salto de línea normalizado
        with open(index_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(index_content)

        # 4. Calcular Hash del index.html generado (Lectura Binaria)
        with open(index_path, "rb") as f:
            index_bytes = f.read()
            index_hash = hashlib.sha256(index_bytes).hexdigest()
            manifest["index.html"] = {"hash": index_hash, "size": len(index_bytes)}

        # 5. Generar manifest.js
        with open(
            os.path.join(cmi_build_dir, "manifest.js"), "w", encoding="utf-8"
        ) as f:
            f.write(f"const SGC_MANIFEST = {json.dumps(manifest, indent=2)};")

        # 6. Empaquetado ZIP
        zip_filename = f"cmi_sgc_{build_date.strftime('%Y%m%d_%H%M')}.zip"
        # Usar settings.MEDIA_ROOT directamente. Si es un Path de unipath, usar str() o .child().
        # settings.py define MEDIA_ROOT = APPS_DIR.child("media")
        # Aseguramos que sea string para os.path.join
        media_root = str(settings.MEDIA_ROOT)
        dest_dir = os.path.join(media_root, "cmi_portatil")
        os.makedirs(dest_dir, exist_ok=True)
        zip_path = os.path.join(dest_dir, zip_filename)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(cmi_build_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, cmi_build_dir)
                    zipf.write(file_path, arcname)

        # 6.5 Copia estática (Requisito 6)
        static_zip_path = os.path.join(dest_dir, "cmi-portatil.zip")
        shutil.copy2(zip_path, static_zip_path)

        # 7. Rotación (Mantener 4 más recientes)
        # Buscar zips en dest_dir
        # Patrón cmi_sgc_*.zip
        list_of_files = glob.glob(os.path.join(dest_dir, "cmi_sgc_*.zip"))
        # Ordenar por tiempo de modificación (mtime) descendente
        list_of_files.sort(key=os.path.getmtime, reverse=True)

        # Borrar los que sobran
        files_to_keep = 4
        for old_file in list_of_files[files_to_keep:]:
            os.remove(old_file)
            self.stdout.write(
                self.style.NOTICE(
                    f"Eliminado backup antiguo: {os.path.basename(old_file)}"
                )
            )

        # Finalización
        duration = time.time() - start_time
        if errors == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Éxito: {zip_filename} generado en {dest_dir}\n"
                    f"Archivos: {len(manifest)} | Tiempo: {duration:.2f}s"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Completado con {errors} errores de archivos no encontrados.\n"
                    f"Paquete generado: {zip_path}"
                )
            )
