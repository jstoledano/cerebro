from django import forms
from apps.pusinex.models import Pusinex, Seccion, Municipio

class PUSINEXForm(forms.ModelForm):
    # Campo auxiliar (no pertenece al modelo) para el filtro en cascada
    municipio_filtro = forms.ModelChoiceField(
        queryset=Municipio.objects.all(),
        required=False,
        label="Municipio",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full', 'id': 'filtro_municipio'})
    )

    class Meta:
        model = Pusinex
        exclude = ('user', )
        widgets = {
            'seccion': forms.Select(attrs={'class': 'select select-bordered w-full', 'id': 'id_seccion'}),
            'f_act': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered w-full'}),
            'hojas': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'min': '1'}),
            'archivo': forms.FileInput(attrs={'class': 'file-input file-input-bordered file-input-primary w-full'}),
            'observaciones': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': '3'}),
        }

    def clean_seccion(self):
        seccion_instance = self.cleaned_data.get('seccion')
        if seccion_instance:
            if not seccion_instance.activa:
                raise forms.ValidationError("No se puede subir un PUSINEX a una sección inactiva (Reseccionada).")
            if seccion_instance.tipo >= 4:
                raise forms.ValidationError("Los PUSINEX solo aplican para secciones Urbanas o Mixtas.")
        return seccion_instance
