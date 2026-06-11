import os
import json
import zipfile
from pathlib import Path

from django.core.serializers import serialize
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.gis.db.models import Union
from django.contrib.gis.geos import MultiPolygon
from django.http import FileResponse
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from .forms import PUSINEXForm
from .models import Entidad, Distrito, Municipio, Seccion, Pusinex

TLAXCALA = 29


class Index(ListView):
    template_name = 'pusinex/index.html'
    model = Distrito
    context_object_name = 'distritos'
    ordering = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entidad = Entidad.objects.get(entidad=TLAXCALA)
        distritos = Distrito.objects.filter(entidad=entidad)

        context["entidad_geojson"] = serialize(
            "geojson", [entidad], geometry_field="geom", fields=("entidad", "nombre")
        )
        context["distritos_geojson"] = serialize(
            "geojson", distritos, geometry_field="geom", fields=("distrito",)
        )

        return context


class SeccionDetail(DetailView):
    model = Seccion
    context_object_name = 'seccion'


class PusinexDetail(DetailView):
    model = Pusinex
    context_object_name = 'pusinex'


class DistritoDetail(DetailView):
    model = Distrito
    context_object_name = "distrito"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["distrito_geojson"] = serialize(
            "geojson",
            [self.object],
            geometry_field="geom",
            fields=("distrito", "cabecera"),
        )

        if not self.object.geom:
            context["municipios_geojson"] = json.dumps(
                {"type": "FeatureCollection", "features": []}
            )
            return context

        municipios = Municipio.objects.filter(seccion__distrito=self.object).distinct()
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
                            "properties": {"id": mun.pk, "nombre": mun.nombre},
                            "geometry": json.loads(geom_final.geojson),
                        }
                    )

        context["municipios_geojson"] = json.dumps(
            {"type": "FeatureCollection", "features": features}
        )

        return context


class MunicipioDetail(ListView):
    context_object_name = 'secciones'
    template_name = 'pusinex/municipio_detail.html'

    def get_context_data(self, **kwargs):
        context = super(MunicipioDetail, self).get_context_data(**kwargs)
        context['municipio'] = Municipio.objects.get(pk=self.kwargs.get('pk'))
        return context

    def get_queryset(self):
        qs = Seccion.objects.filter(municipio=self.kwargs.get('pk'), activa=True).order_by('distrito', 'seccion')
        return qs


class CreatePUSINEX(LoginRequiredMixin, CreateView):
    template_name = 'pusinex/pusinex_form.html'
    form_class = PUSINEXForm
    model = Pusinex
    login_url = reverse_lazy('login')
    redirect_field_name = 'next'

    def form_invalid(self, form):
        return super(CreatePUSINEX, self).form_invalid(form)

    def form_valid(self, form):
        revision = form.save(commit=False)
        revision.user = self.request.user
        revision.save()
        return super(CreatePUSINEX, self).form_valid(form)

    def get_success_url(self):
        return reverse('municipio', kwargs={'pk': self.object.__dict__['municipio'].id})


class Administration(TemplateView):
    template_name = 'pusinex/administration.html'


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


class PUSINEXZip(LoginRequiredMixin, View):
    @staticmethod
    def get(request):
        files = []
        zip_name = Path('media', 'pusinex', '29_pusinex.zip')
        zip_archive = zipfile.ZipFile(zip_name, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=9)
        for p in paquete_total:
            try:
                files.append(p.pusinex_set.latest().archivo.path)
            except Pusinex.DoesNotExist:
                pass
        with zip_archive as archive:
            for file in files:
                archive.write(file, arcname=Path(file).name)
        return FileResponse(open(zip_name, 'rb'))


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
