from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field, Button
from crispy_forms.bootstrap import FormActions
from apps.pusinex.models import Pusinex, Seccion
import logging

logger = logging.getLogger(__name__)


class PUSINEXForm(forms.ModelForm):
    municipio = forms.IntegerField(min_value=1, max_value=60,
                                   widget=forms.Select(attrs={'class': 'select form-select'}))
    seccion = forms.IntegerField(min_value=1, max_value=645,
                                 widget=forms.Select(attrs={'class': 'select form-select'}))
    f_act = forms.DateField(label='Fecha de Actualización', widget=forms.DateInput(attrs={'type': 'date'}))
    hojas = forms.IntegerField(min_value=1)
    archivo = forms.FileField()
    observaciones = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        exclude = ('user', )
        model = Pusinex

    def __init__(self, *args, **kwargs):
        super(PUSINEXForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout (
            Div(
            Field('municipio', wrapper_class='col-5'),
                Field('seccion', wrapper_class='col-2 mb-4'),
                css_class='row'
            ),
            Div(

                Field('f_act', wrapper_class='col-4'),
                Field('hojas', wrapper_class='col-3'),
                css_class='row'
            ),
            Div(
                Field('archivo', wrapper_class='col-10 mb-2'),
                css_class='row'
            ),
            Div(
                Field('observaciones', wrapper_class='col-md-10', rows='3'),
                css_class='row'
            ),
            Div(
                HTML('<hr>'),
                FormActions(
                    Submit('save', 'Guardar cambios'),
                    Button('cancel', 'Cancelar')
                ),
                css_class='modal-footer'
            )
        )

    def clean_seccion(self):
        seccion_id = int(self.cleaned_data['seccion'])
        try:
            seccion_instance = Seccion.objects.get(seccion=seccion_id)
        except Seccion.DoesNotExist:
            raise forms.ValidationError("La sección especificada no existe")
        return seccion_instance
