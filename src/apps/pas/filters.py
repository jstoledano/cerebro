"""Filtros comunes a la consulta web y a la API de evidencias."""
from django import forms
from django.db.models import Q
from django.utils import timezone

ESTADOS = [
    ("terminada", "Terminada"), ("vencida", "Vencida"),
    ("inicia_hoy", "Inicia hoy"), ("vence_hoy", "Vence hoy"),
    ("programada", "Programada"), ("pendiente", "Pendiente"),
]


class EvidenciaFilterForm(forms.Form):
    actividad = forms.IntegerField(required=False, min_value=1)
    ejecucion = forms.IntegerField(required=False, min_value=1)
    responsable = forms.IntegerField(required=False, min_value=1)
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    estado = forms.ChoiceField(required=False, choices=[("", "Todos")] + ESTADOS)

    def clean(self):
        data = super().clean()
        if data.get("desde") and data.get("hasta") and data["desde"] > data["hasta"]:
            raise forms.ValidationError("La fecha inicial debe ser anterior o igual a la final.")
        return data


def filtrar_evidencias(queryset, data):
    campos = {
        "actividad": "ejecucion__ciclo__accion_id",
        "ejecucion": "ejecucion_id",
        "responsable": "ejecucion__responsable_id",
        "desde": "fecha__gte", "hasta": "fecha__lte",
    }
    for parametro, campo in campos.items():
        if data.get(parametro):
            queryset = queryset.filter(**{campo: data[parametro]})
    estado = data.get("estado")
    if estado:
        hoy = timezone.localdate()
        inicio = "ejecucion__ciclo__fecha_inicio"
        fin = "ejecucion__ciclo__fecha_fin"
        estados = {
            "terminada": Q(ejecucion__completada=True),
            "vencida": Q(**{fin + "__lt": hoy}),
            "inicia_hoy": Q(**{inicio: hoy, fin + "__gte": hoy}),
            "vence_hoy": Q(**{fin: hoy}) & ~Q(**{inicio: hoy}),
            "programada": Q(**{inicio + "__gt": hoy, fin + "__gt": hoy}),
            "pendiente": Q(**{inicio + "__lt": hoy, fin + "__gt": hoy}),
        }
        queryset = queryset.filter(estados[estado])
        if estado != "terminada":
            queryset = queryset.filter(ejecucion__completada=False)
    return queryset
