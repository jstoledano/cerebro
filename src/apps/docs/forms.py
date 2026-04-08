"""
Clases forms.py.

Gestiona las clases y funciones de los formularios de la documentación.
"""

# Formularios para la app de documentos
# from captcha.fields import ReCaptchaField
# from captcha.widgets import  ReCaptchaV2Checkbox
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field, Button
from crispy_forms.bootstrap import FormActions
from django import forms

from .models import Documento, Proceso, Tipo, Revision, Reporte

GUARDAR_CAMBIOS = 'Guardar cambios'


INPUT_BASE = 'input input-bordered w-full'
TEXTAREA_BASE = 'textarea textarea-bordered w-full min-h-[140px]'
SELECT_BASE = 'select select-bordered w-full'
TOGGLE_BASE = 'toggle toggle-primary'


class TailwindFormMixin:
    def _apply_tailwind(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('class', TEXTAREA_BASE)
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', SELECT_BASE)
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', TOGGLE_BASE)
            else:
                widget.attrs.setdefault('class', INPUT_BASE)
            widget.attrs.setdefault('placeholder', field.label)


class DocForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para crear un documento nuevo."""

    class Meta:
        model = Documento
        fields = ['nombre', 'proceso', 'tipo', 'ruta', 'texto_ayuda', 'lmd', 'resultados']
        widgets = {
            'texto_ayuda': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_tailwind()
        self.fields['ruta'].widget.attrs.setdefault('type', 'url')


class ProcesoForm(TailwindFormMixin, forms.ModelForm):
    """
    Clase ProcesoForm.

    Formulario simple para crear  un nuevo tipo de proceso.
    """

    def __init__(self, *args, **kwargs):
        """Inicializador del formulario de procesos."""
        super().__init__(*args, **kwargs)
        self._apply_tailwind()

    class Meta:
        """Metadatos de la clase ProcesoForm."""

        model = Proceso
        fields = ['proceso', 'slug']


class TipoForm(TailwindFormMixin, forms.ModelForm):
    """
    Clase TipoForm.

    Formulario simple para crear un nuevo tipo de documento.
    """

    def __init__(self, *args, **kwargs):
        """Inicializador para la clase TipoForm."""
        super().__init__(*args, **kwargs)
        self._apply_tailwind()

    class Meta:
        """Metadatos de la clase TipoForm."""

        model = Tipo
        fields = ['tipo', 'slug']


class ReporteForm(forms.ModelForm):
    """
    Formulario de Reporte.

    Se muestra en un modal para recopilar información de
    documentos obsoletos.
    """
    # captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    class Meta:
        """Metadatos de la clase ReporteForm."""

        model = Reporte
        fields = ['causa', 'descripcion', 'correo']

    def __init__(self, *args, **kwargs):
        """Inicializador de la clase ReporteForm."""
        super(ReporteForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Field('causa', wrapper_class='col-md-12'), css_class='row'),
            Div(Field('descripcion', rows=2, wrapper_class='col-md-12'), css_class='row'),
            Div(Field('correo', wrapper_class='col-md-12'), css_class='row'),
            # Div('captcha', css_class='row'),
            Div(
                HTML('<hr>'),
                FormActions(
                    Submit('cancel', 'Cancelar', css_class='btn btn-secondary'),
                    Submit('save', GUARDAR_CAMBIOS)
                )
            ),
        )


class VersionForm(forms.ModelForm):
    """
    Clase VersionForm.

    Crea una nueva versión del documento dado. Ofrece como sugerencia
    el siguiente número de versión y la fecha actual como fecha de
    actualización.

    Argumentos:
      - doc: Identificador del documento.
    """

    class Meta:
        """Metadatos de VersionForm."""

        model = Revision
        fields = [
            'revision',
            'f_actualizacion',
            'archivo',
            'cambios',
            'notificacion_urgente'
        ]

    def __init__(self, *args, **kwargs):
        """Inicializador de la clase VersionForm."""
        super(VersionForm, self).__init__(*args, **kwargs)
        self.fields['f_actualizacion'].label = "Fecha de Actualización"

        # Aplicar estilos tailwind/daisyui
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('class', TEXTAREA_BASE)
                widget.attrs.setdefault('rows', 3)
            elif isinstance(widget, forms.FileInput):
                widget.attrs.setdefault('class', 'file-input file-input-bordered w-full')
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', TOGGLE_BASE)
            else:
                widget.attrs.setdefault('class', INPUT_BASE)
            widget.attrs.setdefault('placeholder', field.label)

        # Facilitar fecha con input date
        self.fields['f_actualizacion'].widget.input_type = 'date'

        self.helper = FormHelper()
        self.helper.form_id = 'formulario_revision'
        self.helper.layout = Layout(
            Div(
                Field('revision', wrapper_class='col-md-6', attrs={
                    "label": self.instance.revision
                }),
                Field('f_actualizacion', wrapper_class='col-md-6', attrs={
                    "label": "Fecha de Actualización"
                }),
                css_class='row'
            ),
            Div(
                Field('archivo', wrapper_class='col-md-12'),
                css_class='row'
            ),
            Div(
                Field('cambios', wrapper_class='col', rows=3),
                css_class='row'
            ),
            Div(
                Field('notificacion_urgente', wrapper_class='col-md-12', css_class='form-check-input'),
                css_class='form-check form-switch row'
            ),
            Div(
                HTML('<hr>'),
                FormActions(
                    Submit('save', GUARDAR_CAMBIOS)
                )
            )
        )


class PanicResolveForm(forms.ModelForm):
    """
    Clase PanicResolveForm.

    Formulario para resolver un documento en estado de pánico.
    """

    class Meta:
        model = Reporte
        fields = ['resuelto', 'resolucion']

    def __init__(self, *args, **kwargs):
        """Inicializa el formulario."""
        super(PanicResolveForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Field('resolucion', rows=3), css_class='row'),
            Div(Field('resuelto', css_class='form-check-input'), css_class='sform-check form-switch'),
            Div(
                HTML('<hr>'),
                FormActions(
                    Submit('cancel', 'Cancelar', css_class='btn btn-secondary'),
                    Submit('save', GUARDAR_CAMBIOS)
                )
            ),
        )
