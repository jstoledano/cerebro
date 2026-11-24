"""Expediente Distrito Local: vistas y GeoJSON informativos del MGE existente."""
import json
from django.conf import settings
from django.core.serializers import serialize
from django.views.generic import DetailView
from .models import DistritoLocal, Seccion


class DistritoLocalDetail(DetailView):
    model = DistritoLocal
    context_object_name = 'distrito_local'
    template_name = 'pusinex/distrito_local_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        distrito = self.object
        sections = list(Seccion.objects.filter(distrito_l=distrito, activa=True)
                        .select_related('municipio', 'distrito').order_by('municipio_id', 'seccion'))
        municipios = {}
        distritos_federales = {}
        for sec in sections:
            m = municipios.setdefault(sec.municipio_id, {
                'numero': sec.municipio_id, 'nombre': sec.municipio.nombre, 'secciones': 0,
            })
            m['secciones'] += 1
            f = distritos_federales.setdefault(sec.distrito_id, {'numero': sec.distrito_id, 'secciones': 0})
            f['secciones'] += 1
        ctx.update({
            'secciones': sections,
            'secciones_conteo': len(sections),
            'municipios': sorted(municipios.values(), key=lambda x: x['numero']),
            'distritos_federales': sorted(distritos_federales.values(), key=lambda x: x['numero']),
            'padron_total': sum(s.pe for s in sections),
            'lista_nominal_total': sum(s.ln for s in sections),
            'distrito_local_geojson': serialize('geojson', [distrito], geometry_field='geom', fields=('distrito_local', 'cabecera')),
            'secciones_geojson': serialize('geojson', sections, geometry_field='geom', fields=('seccion',)),
            'carto_basemaps_api_key': settings.CARTO_BASEMAPS_API_KEY,
        })
        return ctx
