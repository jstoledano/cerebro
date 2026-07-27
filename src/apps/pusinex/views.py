import csv
import os
import json
import zipfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.contrib import messages
from django.db.models import OuterRef, Subquery, Sum
from django.core.serializers import serialize
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.gis.geos import MultiPolygon
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView
from django.utils import timezone

from .forms import PUSINEXForm
from .models import Entidad, Distrito, Municipio, Seccion, Pusinex

TLAXCALA = 29
PACKAGE_DIRECTORY = Path(settings.MEDIA_ROOT) / "pusinex" / "paquetes"
STATE_PACKAGE_FILENAME = "29_pusinex_estatal.zip"
DISTRICT_PACKAGE_FILENAME = "29_pusinex_distrito_{district:02d}.zip"
MANIFEST_FILENAME = "MANIFIESTO.csv"


def get_pusinex_package_path(district=None):
    """Devuelve la ruta estable del paquete estatal o distrital."""
    if district is None:
        filename = STATE_PACKAGE_FILENAME
    else:
        filename = DISTRICT_PACKAGE_FILENAME.format(district=int(district))

    return PACKAGE_DIRECTORY / filename


def get_latest_pusinex_entries(district=None):
    """Obtiene una entrada por sección válida con su revisión más reciente."""
    latest_revision = Pusinex.objects.filter(
        seccion_id=OuterRef("pk")
    ).order_by("-f_act", "-pk")

    sections = Seccion.objects.filter(
        entidad_id=TLAXCALA,
        activa=True,
        tipo__lt=4,
    ).select_related("distrito", "municipio")

    if district is not None:
        sections = sections.filter(distrito__distrito=int(district))

    sections = list(
        sections.annotate(
            latest_pusinex_id=Subquery(latest_revision.values("pk")[:1])
        ).order_by(
            "distrito__distrito",
            "municipio__municipio",
            "seccion",
        )
    )

    latest_ids = [
        section.latest_pusinex_id
        for section in sections
        if section.latest_pusinex_id is not None
    ]
    pusinex_by_id = {
        pusinex.pk: pusinex
        for pusinex in Pusinex.objects.filter(pk__in=latest_ids)
    }

    entries = []
    for section in sections:
        pusinex = pusinex_by_id.get(section.latest_pusinex_id)
        status = "INCLUIDO"
        observation = ""
        source_path = None
        filename = ""
        revision_date = ""

        if pusinex is None:
            status = "SIN_REGISTRO"
            observation = "La sección carece de registros PUSINEX."
        else:
            revision_date = pusinex.f_act.isoformat()

            if not pusinex.archivo:
                status = "SIN_ARCHIVO"
                observation = "La revisión más reciente carece de archivo asociado."
            elif not pusinex.archivo.storage.exists(pusinex.archivo.name):
                status = "ARCHIVO_NO_ENCONTRADO"
                observation = "El archivo registrado no existe en el almacenamiento."
                filename = Path(pusinex.archivo.name).name
            else:
                source_path = Path(pusinex.archivo.path)
                filename = source_path.name

        entries.append(
            {
                "section": section,
                "pusinex": pusinex,
                "source_path": source_path,
                "filename": filename,
                "revision_date": revision_date,
                "status": status,
                "observation": observation,
            }
        )

    return entries


def get_pusinex_coverage_statistics(entries):
    """Resume la cobertura PUSINEX de un conjunto de secciones elegibles."""
    status_counts = {
        "SIN_REGISTRO": 0,
        "SIN_ARCHIVO": 0,
        "ARCHIVO_NO_ENCONTRADO": 0,
    }
    with_pusinex = 0

    for entry in entries:
        status = entry["status"]
        if status == "INCLUIDO":
            with_pusinex += 1
        elif status in status_counts:
            status_counts[status] += 1

    eligible = len(entries)
    missing = eligible - with_pusinex
    coverage = round((with_pusinex * 100) / eligible, 1) if eligible else 0.0

    return {
        "eligible": eligible,
        "with_pusinex": with_pusinex,
        "missing": missing,
        "coverage": coverage,
        "without_record": status_counts["SIN_REGISTRO"],
        "without_file": status_counts["SIN_ARCHIVO"],
        "file_not_found": status_counts["ARCHIVO_NO_ENCONTRADO"],
    }


def build_pusinex_manifest(entries):
    """Construye el manifiesto CSV que se agrega dentro de cada paquete."""
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "distrito",
            "municipio",
            "seccion",
            "fecha_revision",
            "nombre_archivo",
            "estado",
            "observacion",
        ]
    )

    for entry in entries:
        section = entry["section"]
        writer.writerow(
            [
                f"{section.distrito.distrito:02d}",
                f"{section.municipio.municipio:03d}",
                f"{section.seccion:04d}",
                entry["revision_date"],
                entry["filename"],
                entry["status"],
                entry["observation"],
            ]
        )

    return output.getvalue()


def build_pusinex_package(district=None):
    """Genera atómicamente un paquete estatal o distrital."""
    PACKAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    target_path = get_pusinex_package_path(district=district)
    entries = get_latest_pusinex_entries(district=district)

    included_entries = [
        entry for entry in entries if entry["status"] == "INCLUIDO"
    ]
    omitted_entries = [
        entry for entry in entries if entry["status"] != "INCLUIDO"
    ]

    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            prefix=f".{target_path.stem}_",
            suffix=".tmp",
            dir=PACKAGE_DIRECTORY,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for entry in included_entries:
                archive.write(
                    entry["source_path"],
                    arcname=entry["filename"],
                )

            archive.writestr(
                MANIFEST_FILENAME,
                build_pusinex_manifest(entries).encode("utf-8-sig"),
            )

        os.replace(temporary_path, target_path)
    except Exception:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        raise

    return {
        "district": district,
        "path": target_path,
        "filename": target_path.name,
        "sections": len(entries),
        "included": len(included_entries),
        "omitted": len(omitted_entries),
        "omissions": omitted_entries,
    }


def build_all_pusinex_packages():
    """Genera el paquete estatal y un paquete por distrito de Tlaxcala."""
    state_result = build_pusinex_package()
    district_results = []

    district_numbers = Distrito.objects.filter(
        entidad_id=TLAXCALA
    ).order_by("distrito").values_list("distrito", flat=True)

    for district_number in district_numbers:
        district_results.append(
            build_pusinex_package(district=district_number)
        )

    return {
        "state": state_result,
        "districts": district_results,
    }


def get_pusinex_package_metadata(district=None):
    """Devuelve los datos públicos de un paquete previamente generado."""
    package_path = get_pusinex_package_path(district=district)
    exists = package_path.is_file()

    if district is None:
        download_url = reverse("pusinex:state_package")
    else:
        download_url = reverse(
            "pusinex:district_package",
            kwargs={"pk": int(district)},
        )

    metadata = {
        "district": district,
        "path": package_path,
        "filename": package_path.name,
        "exists": exists,
        "size": None,
        "modified": None,
        "download_url": download_url,
    }

    if exists:
        stat = package_path.stat()
        metadata.update(
            {
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.get_current_timezone(),
                ),
            }
        )

    return metadata


def open_pusinex_package(package_path):
    """Entrega un paquete generado o responde con 404 cuando aún no existe."""
    if not package_path.is_file():
        raise Http404("El paquete PUSINEX solicitado aún no ha sido generado.")

    return FileResponse(
        package_path.open("rb"),
        as_attachment=True,
        filename=package_path.name,
        content_type="application/zip",
    )


class Index(ListView):
    template_name = 'pusinex/index.html'
    model = Distrito
    context_object_name = 'distritos'
    ordering = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entidad = Entidad.objects.get(entidad=TLAXCALA)
        distritos = Distrito.objects.filter(entidad=entidad)

        # --- CÁLCULO DE ESTADÍSTICAS ESTATALES ---
        # Sumamos el padrón y lista nominal de todas las secciones activas
        totales = Seccion.objects.filter(activa=True).aggregate(
            padron=Sum('pe'),
            nominal=Sum('ln')
        )
        secciones_conteo = Seccion.objects.filter(activa=True).count()

        context.update({
            "entidad_geojson": serialize(
                "geojson", [entidad], geometry_field="geom", fields=("entidad", "nombre")
            ),
            "distritos_geojson": serialize(
                "geojson", distritos, geometry_field="geom", fields=("distrito",)
            ),
            # Nuevas variables para la plantilla
            "secciones_conteo": secciones_conteo,
            "padron_total": totales['padron'] or 0,
            "lista_nominal_total": totales['nominal'] or 0,
        })

        return context


class SeccionDetail(DetailView):
    model = Seccion
    context_object_name = "seccion"
    template_name = "pusinex/seccion_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. RUTAS: De distrito.ubica (origen) a seccion.ubica (destino)
        origen = (
            self.object.distrito.ubica.strip()
            if self.object.distrito and self.object.distrito.ubica
            else ""
        )
        destino = self.object.ubica.strip() if self.object.ubica else ""

        if origen and destino:
            ruta_url = f"https://maps.google.com/maps?saddr={origen}&daddr={destino}&output=embed"
        else:
            ruta_url = ""

        # 2. MAPAS: Generación de GeoJSON
        seccion_geo = serialize(
            "geojson", [self.object], geometry_field="geom", fields=("seccion", "tipo")
        )

        # Traemos el municipio completo para dar contexto visual en el fondo
        municipio_geo = serialize(
            "geojson",
            [self.object.municipio],
            geometry_field="geom",
            fields=("municipio", "nombre"),
        )

        # 3. PUSINEX: Extraer el registro más reciente
        try:
            ultimo_pusinex = self.object.pusinex_set.latest()
        except Pusinex.DoesNotExist:
            ultimo_pusinex = None

        # --- NUEVA LÓGICA SEGURA PARA EL TIPO DE SECCIÓN ---
        # Forzamos la conversión a entero con Python puro. Si por alguna
        # razón la BD tiene basura, asumimos que es rural (99) por seguridad.
        try:
            tipo_seccion = int(self.object.tipo)
        except (ValueError, TypeError):
            tipo_seccion = 99

        es_urbana = tipo_seccion < 4
        # ---------------------------------------------------

        # 4. DECLARACIÓN DEL CONTEXTO
        context.update(
            {
                "ruta": ruta_url,
                "seccion_geojson": seccion_geo,
                "municipio_geojson": municipio_geo,
                "ultimo_pusinex": ultimo_pusinex,
                "es_urbana": es_urbana,  # <--- Pasamos el booleano limpio a la plantilla
            }
        )

        return context


class PusinexDetail(DetailView):
    model = Pusinex
    context_object_name = 'pusinex'


class DistritoDetail(DetailView):
    model = Distrito
    context_object_name = "distrito"

    def get_context_data(self, **kwargs):
        # 1. Inicializamos el contexto base
        context = super().get_context_data(**kwargs)

        # 2. OPERACIONES Y CÁLCULOS

        # Generación de la ruta
        origen = (
            self.object.entidad.ubica.strip()
            if self.object.entidad and self.object.entidad.ubica
            else ""
        )
        destino = self.object.ubica.strip() if self.object.ubica else ""

        # Construcción del enlace para IFRAME usando saddr (origen) y daddr (destino)
        if origen and destino:
            ruta_url = f"https://maps.google.com/maps?saddr={origen}&daddr={destino}&output=embed"
        else:
            ruta_url = ""

        # Consultas de secciones
        secciones_qs = self.object.seccion_set.filter(activa=True).order_by(
            "distrito", "municipio", "seccion"
        )
        secciones_totales = secciones_qs.count()

        # Generación de GeoJSON del Distrito
        distrito_geo = serialize(
            "geojson",
            [self.object],
            geometry_field="geom",
            fields=("distrito", "cabecera"),
        )

        # Generación de GeoJSON de Municipios
        municipios_geo_dict = {"type": "FeatureCollection", "features": []}

        if self.object.geom:
            municipios = Municipio.objects.filter(
                seccion__distrito=self.object
            ).distinct()
            features = []

            for mun in municipios:
                if not mun.geom:
                    continue

                # Clonar geometrías y asegurar concordancia de SRID antes de la intersección en GEOS
                mun_geom = mun.geom.clone().buffer(0)
                distrito_geom = self.object.geom.clone().buffer(0)

                if distrito_geom.srid != mun_geom.srid:
                    distrito_geom.transform(mun_geom.srid)

                fragmento = mun_geom.intersection(distrito_geom)

                if fragmento and not fragmento.empty:
                    poly_list = []

                    # Extraer estrictamente componentes bidimensionales (Polígonos)
                    if fragmento.geom_type == "Polygon":
                        poly_list.append(fragmento)
                    elif fragmento.geom_type == "MultiPolygon":
                        poly_list.extend(fragmento)
                    elif fragmento.geom_type == "GeometryCollection":
                        for g in fragmento:
                            if g.geom_type == "Polygon":
                                poly_list.append(g)
                            elif g.geom_type == "MultiPolygon":
                                poly_list.extend(g)

                    if poly_list:
                        # Construir el MultiPolygon garantizando el SRID nativo antes de transformar a WGS84
                        geom_final = MultiPolygon(*poly_list, srid=mun_geom.srid)
                        geom_final.transform(4326)

                        features.append(
                            {
                                "type": "Feature",
                                "properties": {
                                    "id": mun.municipio,
                                    "nombre": mun.nombre,
                                },
                                "geometry": json.loads(geom_final.geojson),
                            }
                        )

            municipios_geo_dict["features"] = features

        # 3. DECLARACIÓN DEL CONTEXTO
        context.update(
            {
                "ruta": ruta_url,
                "distrito_geojson": distrito_geo,
                "municipios_geojson": json.dumps(municipios_geo_dict),
                "secciones_conteo": secciones_totales,
                "secciones": secciones_qs,
                "padron_total": self.object.pe,
                "lista_nominal_total": self.object.ln,
                "district_package": get_pusinex_package_metadata(
                    district=self.object.distrito
                ),
            }
        )

        return context


class MunicipioDetail(DetailView):
    model = Municipio
    context_object_name = "municipio"
    template_name = "pusinex/municipio_detail.html"

    def get_context_data(self, **kwargs):
        # 1. Inicializamos el contexto base
        context = super().get_context_data(**kwargs)

        # 2. OPERACIONES Y CÁLCULOS

        # Consultas de secciones activas correspondientes al municipio
        secciones_qs = self.object.seccion_set.filter(activa=True).order_by(
            "distrito", "seccion"
        )
        secciones_totales = secciones_qs.count()

        # Generación de GeoJSON del contorno del Municipio
        municipio_geo = serialize(
            "geojson",
            [self.object],
            geometry_field="geom",
            fields=("municipio", "nombre"),
        )

        # Generación de GeoJSON de las Secciones internas (para la capa secundaria del mapa)
        secciones_geo = serialize(
            "geojson", secciones_qs, geometry_field="geom", fields=("seccion",)
        )

        # 3. DECLARACIÓN DEL CONTEXTO
        # Tomamos padron y lista_nominal directamente del objeto Municipio gracias al ETL
        context.update(
            {
                "municipio_geojson": municipio_geo,
                "secciones_geojson": secciones_geo,
                "secciones_conteo": secciones_totales,
                "secciones": secciones_qs,
                "padron_total": self.object.pe,
                "lista_nominal_total": self.object.ln,
            }
        )

        return context


class CreatePUSINEX(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "pusinex.add_pusinex"
    template_name = "pusinex/pusinex_form.html"
    form_class = PUSINEXForm
    model = Pusinex
    success_url = reverse_lazy(
        "pusinex:administration"
    )  # Redirige al panel de administración al guardar

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # MAGIA: Pre-cargamos la relación Municipio -> Secciones activas y urbanas en un JSON
        secciones_validas = Seccion.objects.filter(activa=True, tipo__lt=4).values(
            "municipio_id", "seccion"
        )
        diccionario_secciones = {}
        for s in secciones_validas:
            m_id = s["municipio_id"]
            if m_id not in diccionario_secciones:
                diccionario_secciones[m_id] = []
            diccionario_secciones[m_id].append(s["seccion"])

        context["secciones_json"] = json.dumps(diccionario_secciones)
        return context

    def form_valid(self, form):
        revision = form.save(commit=False)
        revision.user = self.request.user
        revision.save()
        return super().form_valid(form)


class Administration(TemplateView):
    template_name = "pusinex/administration.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        districts = list(
            Distrito.objects.filter(entidad_id=TLAXCALA).order_by("distrito")
        )

        state_entries = get_latest_pusinex_entries()
        entries_by_district = {
            district.distrito: []
            for district in districts
        }
        for entry in state_entries:
            district_number = entry["section"].distrito.distrito
            entries_by_district.setdefault(district_number, []).append(entry)

        district_packages = []
        for district in districts:
            district_entries = entries_by_district.get(district.distrito, [])
            district_packages.append(
                {
                    "district": district,
                    "package": get_pusinex_package_metadata(
                        district=district.distrito
                    ),
                    "statistics": get_pusinex_coverage_statistics(
                        district_entries
                    ),
                }
            )

        context.update(
            {
                "state_package": get_pusinex_package_metadata(),
                "state_statistics": get_pusinex_coverage_statistics(
                    state_entries
                ),
                "district_packages": district_packages,
            }
        )
        return context


class LogoutView(TemplateView):
    next_page = reverse_lazy('index')
    redirect_field_name = 'next'


seccionesVNM2023 = (
    12, 14, 16, 17, 26, 27, 30, 34, 36, 43, 48, 74, 107, 184, 188,
    201, 203, 218, 261, 409, 414, 474, 478, 482, 506, 542, 543,
    533, 534, 606, 9, 124, 134, 141, 147, 266, 348, 349, 355, 363,
    364, 384, 624, 397, 441, 442, 469, 626, 567, 392, 159, 151, 2,
    78, 85, 87, 89, 234, 242, 290, 297, 325, 336, 425, 511, 512,
    515, 575, 581, 589, 593, 597, 314, 551, 473, 142)

seccionesVNM2024 = (
    14, 19, 26, 635, 68, 100, 102, 107, 109, 191, 213, 217, 365, 403,
    406, 421, 471, 484, 521, 530, 536, 543, 78, 88, 90, 165, 168, 220,
    232, 240, 253, 256, 257, 299, 333, 336, 347, 437, 439, 440, 444,
    446, 457, 464, 467, 626, 629, 509, 550, 556, 643, 295, 296, 126,
    139, 141, 144, 145, 266, 271, 283, 348, 355, 356, 360, 622, 623,
    639, 374, 375, 381, 382, 384, 561, 572, 597, 599, 154
)
queryVNM2023 = Seccion.objects.filter(seccion__in=seccionesVNM2023).order_by('distrito', 'seccion')
pusinexVNM2023 = Pusinex.objects.filter(seccion__seccion__in=seccionesVNM2023)

queryVNM2024 = Seccion.objects.filter(seccion__in=seccionesVNM2024, tipo__lt=4, activa=True)\
    .order_by('distrito', 'municipio', 'seccion')
pusinexVNM2024 = Pusinex.objects.filter(seccion__seccion__in=seccionesVNM2024)
paquete_total = Seccion.objects.filter(tipo__lt=4, activa=True).order_by('distrito', 'municipio', 'seccion')


class VNM2024(ListView):
    model = Seccion

    def get_queryset(self):
        qs = queryVNM2024
        return qs


class VNM2023(ListView):
    model = Seccion

    def get_queryset(self):
        qs = queryVNM2023
        return qs


class VNMZipView(View):
    @staticmethod
    def get(request, dto):
        files = []
        zip_name = Path('media', 'pusinex', f'pusinex_VNM_0{dto}.zip')
        zip_archive = zipfile.ZipFile(zip_name, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=9)
        if dto:
            for p in pusinexVNM2024.filter(seccion__distrito__distrito=dto):
                files.append(Path(os.getcwd(), 'media', p.archivo.path))
        with zip_archive as archive:
            for file in files:
                archive.write(file, arcname=Path(file).name)
        return FileResponse(open(zip_name, 'rb'))


class GeneratePUSINEXPackages(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    """Regenera el paquete estatal y todos los paquetes distritales."""

    permission_required = "pusinex.generate_pusinex_packages"
    raise_exception = True

    def post(self, request):
        try:
            results = build_all_pusinex_packages()
        except Exception:
            messages.error(
                request,
                "No fue posible generar los paquetes PUSINEX.",
            )
            return redirect("pusinex:administration")

        generated = [results["state"], *results["districts"]]
        summary = [
            f"Estatal: {results['state']['included']} archivos"
        ]
        summary.extend(
            (
                f"Distrito {int(result['district']):02d}: "
                f"{result['included']} archivos"
            )
            for result in results["districts"]
        )

        messages.success(
            request,
            "Paquetes PUSINEX generados. " + "; ".join(summary) + ".",
        )

        omitted = sum(result["omitted"] for result in generated)
        if omitted:
            messages.warning(
                request,
                (
                    f"Los manifiestos registran {omitted} omisiones "
                    "acumuladas. Cada sección ausente aparece en el paquete "
                    "estatal y en su paquete distrital."
                ),
            )

        return redirect("pusinex:administration")


class StatePUSINEXPackageDownload(View):
    """Descarga pública del paquete estatal previamente generado."""

    def get(self, request):
        return open_pusinex_package(get_pusinex_package_path())


class DistrictPUSINEXPackageDownload(View):
    """Descarga pública del paquete correspondiente a un distrito."""

    def get(self, request, pk):
        district = Distrito.objects.filter(
            entidad_id=TLAXCALA,
            distrito=pk,
        ).first()
        if district is None:
            raise Http404("El distrito solicitado no existe.")

        return open_pusinex_package(
            get_pusinex_package_path(district=district.distrito)
        )


YEAR_LATEST_PUSINEX = 2024


class PUSINEXByYear(ListView):
    """Lista las secciones con PUSINEX actualizados por año."""
    model = Pusinex
    template_name = 'pusinex/pusinex_by_year.html'

    def get_context_data(self, **kwargs):
        context = super(PUSINEXByYear, self).get_context_data(**kwargs)
        context['year'] = self.kwargs.get('year')
        return context

    def get_queryset(self):
        """Muestra las secciones con PUSINEX actualizados en el año seleccionado como valores únicos."""
        qs = Pusinex.objects.filter(updated__year=self.kwargs.get('year')).order_by("updated", "seccion")
        return qs


class PUSINEXLastUpdate(ListView):
    """Lista las secciones con PUSINEX actualizados por año."""
    model = Pusinex
    template_name = 'pusinex/pusinex_last_update.html'

    def get_context_data(self, **kwargs):
        context = super(PUSINEXLastUpdate, self).get_context_data(**kwargs)
        # Se obtienen los años en los que se han actualizado los PUSINEX como valores
        # únicos para mostrar en la plantilla.
        context['years'] = Pusinex.objects.values_list('updated__year', flat=True).distinct().order_by('updated__year')
        context['year'] = YEAR_LATEST_PUSINEX
        return context

    def get_queryset(self):
        """Muestra las secciones con PUSINEX actualizados en el año seleccionado como valores únicos."""
        qs = Pusinex.objects.filter(updated__year=YEAR_LATEST_PUSINEX).order_by("updated", "seccion")
        return qs
