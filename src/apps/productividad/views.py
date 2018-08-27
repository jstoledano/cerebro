# coding: utf-8
# app: apps.productividad.views
# author: Javier Sanchez Toledano <js.toledano@me.com>
# date: 26/08/2018
"""Vista para subir el archivo de la productividad."""

import math
import xlrd
from django.urls import reverse_lazy
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.generic.list import ListView
from django.views.generic.edit import FormView
from django.views.generic.detail import DetailView
from django.conf import settings
from core.utils import Remesa
from apps.productividad.forms import CargaCifras
from apps.productividad.models import Reporte, Cifras


def get_int(celda):
    """Convierte el valor de una celda en entero"""
    try:
        if celda.ctype == 5:
            return 0
        return math.ceil(celda.value)
    except ValueError:
        return 0


def procesar_cifras(archivo_excel):
    """Procesa el archivo de cifras"""
    cifras = xlrd.open_workbook(archivo_excel).sheet_by_name("CIFRAS_PRODUCCION DIARIA")
    remesa = cifras.cell(6, 10).value[8:].replace('_', '-')
    observaciones = cifras.cell(33, 0).value
    macs = {}

    for row in range(8, 30):
        mac = cifras.row(row)
        try:
            modulo = str(int(mac[0].value))
            if modulo[:3] == '290':
                macs[modulo] = {
                    'distrito': modulo[2:4],
                    'tipo': mac[1].value,
                    'dias_trabajados': get_int(mac[2]),
                    'jornada_trabajada': mac[3].value,
                    'configuracion': mac[4].value,
                    'tramites': get_int(mac[5]),
                    'credenciales_entregadas_actualizacion': get_int(mac[6]),
                    'credenciales_reimpresion': get_int(mac[7]),
                    'total_atenciones': get_int(mac[8]),
                    'productividad_x_dia': get_int(mac[9]),
                    'productividad_x_dia_x_estacion': get_int(mac[10]),
                    'credenciales_recibidas': get_int(mac[12])
                }
        except ValueError:
            pass

    return observaciones, remesa, macs


class CifrasPortada(ListView):
    """Para crear la portada"""
    model = Reporte
    template_name = 'productividad/index.html'
    context_object_name = 'reportes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Productividad"
        return context


class RemesaDetalle(DetailView):
    """Clase para visualizar el informe de productividad"""
    model = Reporte
    template_name = 'productividad/remesa_detalle.html'
    context_object_name = 'reporte'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rem'] = Remesa.objects.get(remesa=self.object.remesa[:7])
        context['title'] = 'Reporte de productividad en los módulos de atención ciudadana'
        return context


class CifrasUpload(FormView):
    """Con esta clase subo el archivo"""
    form_class = CargaCifras
    success_url = reverse_lazy('cifras:index')
    template_name = 'productividad/add.html'

    def form_valid(self, form):
        fecha = form.cleaned_data['fecha_corte']
        archivo = self.get_form_kwargs().get('files')['archivo']
        path = default_storage.save(
            settings.MEDIA_ROOT.child('productividad', f"remesa-{fecha.strftime('%Y%m%d')}.xls"),
            ContentFile(archivo.read())
        )
        (observaciones, remesa, macs) = procesar_cifras(path)
        reporte, created = Reporte.objects.update_or_create(
            remesa=remesa,
            defaults={
                'fecha_corte': fecha,
                'remesa': remesa,
                'notas': observaciones,
                'archivo': path,
                'usuario': self.request.user
            }
        )
        print(f"cerebro:: El reporte {reporte} se creó en {created}")
        for mac in macs:
            cifras, created = Cifras.objects.update_or_create(
                reporte_semanal=reporte, modulo=mac,
                defaults={
                    'reporte_semanal': reporte,
                    'distrito': macs[mac]['distrito'],
                    'modulo': mac,
                    'tipo': macs[mac]['tipo'],
                    'dias_trabajados': macs[mac]['dias_trabajados'],
                    'jornada_trabajada': macs[mac]['jornada_trabajada'],
                    'configuracion': macs[mac]['configuracion'],
                    'tramites': macs[mac]['tramites'],
                    'credenciales_entregadas_actualizacion':
                        macs[mac]['credenciales_entregadas_actualizacion'],
                    'credenciales_reimpresion': macs[mac]['credenciales_reimpresion'],
                    'total_atenciones': macs[mac]['total_atenciones'],
                    'productividad_x_dia': macs[mac]['productividad_x_dia'],
                    'productividad_x_dia_x_estacion': macs[mac]['productividad_x_dia_x_estacion'],
                    'credenciales_recibidas': macs[mac]['credenciales_recibidas']
                }
            )
            print(f'cerebro:: Se crearon los datos {mac} en el registro {cifras} el {created}')
        return super().form_valid(form)
