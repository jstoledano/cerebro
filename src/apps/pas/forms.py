from django import forms
from django.contrib.auth import get_user_model
from django.forms import (
    TextInput,
    NumberInput,
    EmailInput,
    DateInput,
    TimeInput,
    URLInput,
    Select,
    SelectMultiple,
    Textarea,
    CheckboxInput,
    ClearableFileInput,
)

from .models import (
    Plan,
    Accion,
    Seguimiento,
    Evidencia,
    AMBITO,
)


User = get_user_model()


WIDGET_CLASS_MAP = {
    TextInput: 'input input-bordered w-full',
    NumberInput: 'input input-bordered w-full',
    EmailInput: 'input input-bordered w-full',
    DateInput: 'input input-bordered w-full',
    TimeInput: 'input input-bordered w-full',
    URLInput: 'input input-bordered w-full',
    Select: 'select select-bordered w-full',
    SelectMultiple: 'select select-bordered w-full',
    Textarea: 'textarea textarea-bordered w-full min-h-[160px]',
    CheckboxInput: 'toggle toggle-primary',
    ClearableFileInput: 'file-input file-input-bordered w-full',
}


def apply_tailwind_widgets(form):
    for field in form.fields.values():
        widget = field.widget
        for widget_type, css_class in WIDGET_CLASS_MAP.items():
            if isinstance(widget, widget_type):
                existing = widget.attrs.get('class', '')
                widget.attrs['class'] = f'{existing} {css_class}'.strip()
                break


class ResponsableChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        full_name = (obj.get_full_name() or '').strip()
        if full_name:
            return full_name
        return obj.email or obj.username


class PlanForm(forms.ModelForm):
    otra_fuente = forms.CharField(
        label='Otra fuente',
        required=False,
        widget=forms.TextInput(attrs={'disabled': 'disabled'})
    )

    class Meta:
        model = Plan
        exclude = [
            "user",
            "eliminacion",
            "txt_eliminacion",
            "recurrencia",
            "txt_recurrencia",
        ]
        widgets = {
            'fecha_llenado': DateInput(attrs={'type': 'date'}),
            'fecha_inicio': DateInput(attrs={'type': 'date'}),
            'fecha_termino': DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        fuente = cleaned_data.get("fuente")
        otra_fuente = cleaned_data.get("otra_fuente")

        if fuente == 9 and not otra_fuente:
            self.add_error(
                "otra_fuente", "Este campo es obligatorio si seleccionó Otros"
            )

        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_termino = cleaned_data.get("fecha_termino")

        if fecha_inicio and fecha_termino and fecha_inicio > fecha_termino:
            self.add_error(
                "fecha_termino",
                "La fecha de término no puede ser anterior a la fecha de inicio.",
            )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_tailwind_widgets(self)


class AccionForm(forms.ModelForm):
    responsable = ResponsableChoiceField(
        queryset=User.objects.order_by(
            "first_name",
            "last_name",
            "email",
        ),
        required=False,
        label="Responsable directo",
        help_text=(
            "Úsalo cuando la actividad corresponda "
            "a una persona concreta."
        ),
    )

    ambitos = forms.MultipleChoiceField(
        choices=AMBITO,
        required=False,
        label="Ámbitos de ejecución",
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            "Selecciona los ámbitos en los que se "
            "ejecutará esta actividad."
        ),
    )

    class Meta:
        model = Accion
        exclude = [
            "user",
            "plan",
        ]

        widgets = {
            "fecha_inicio": DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "fecha_fin": DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "responsable"
        ].empty_label = "Sin responsable directo"

        if self.instance and self.instance.pk:
            self.fields["ambitos"].initial = (
                self.instance.ambitos or []
            )

        apply_tailwind_widgets(self)

    def clean(self):
        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get(
            "fecha_inicio"
        )

        fecha_fin = cleaned_data.get(
            "fecha_fin"
        )

        if (
            fecha_inicio
            and fecha_fin
            and fecha_inicio > fecha_fin
        ):
            self.add_error(
                "fecha_fin",
                (
                    "La fecha de término no puede "
                    "ser anterior a la fecha de inicio."
                ),
            )

        ambitos = cleaned_data.get(
            "ambitos"
        ) or []

        cleaned_data["ambitos"] = list(
            ambitos
        )

        puesto_responsable = (
            cleaned_data.get(
                "puesto_responsable"
            )
        )

        responsable = cleaned_data.get(
            "responsable"
        )

        if (
            len(ambitos) > 1
            and not puesto_responsable
        ):
            self.add_error(
                "puesto_responsable",
                (
                    "Para una actividad con varios "
                    "ámbitos selecciona el puesto "
                    "responsable."
                ),
            )

        if (
            len(ambitos) <= 1
            and not puesto_responsable
            and not responsable
        ):
            self.add_error(
                "responsable",
                (
                    "Selecciona un responsable directo "
                    "o un puesto responsable."
                ),
            )

        if not self.instance.pk:
            return cleaned_data

        original = Accion.objects.get(
            pk=self.instance.pk
        )

        estructura_modificada = any(
            [
                original.periodicidad
                != cleaned_data.get(
                    "periodicidad"
                ),
                set(original.ambitos or [])
                != set(ambitos),
                original.fecha_inicio
                != fecha_inicio,
                original.fecha_fin
                != fecha_fin,
                original.formato_evidencia
                != cleaned_data.get(
                    "formato_evidencia"
                ),
                original.puesto_responsable
                != puesto_responsable,
            ]
        )

        if not estructura_modificada:
            return cleaned_data

        tiene_evidencias = (
            Evidencia.objects
            .filter(
                ejecucion__ciclo__accion=original
            )
            .exists()
        )

        if tiene_evidencias:
            raise forms.ValidationError(
                (
                    "No es posible modificar la "
                    "estructura de esta actividad "
                    "porque ya tiene evidencias "
                    "registradas."
                )
            )

        return cleaned_data


class SeguimientoForm(forms.ModelForm):
    responsable = ResponsableChoiceField(
        queryset=User.objects.order_by('first_name', 'last_name', 'email'),
        required=False,
        label='Responsable',
        help_text='Persona responsable de la actualización',
    )

    class Meta:
        model = Seguimiento
        exclude = ['user', 'accion']
        widgets = {
            'fecha': DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].empty_label = 'Selecciona un responsable'
        apply_tailwind_widgets(self)


class PlanClosureForm(forms.Form):
    RESULTADO_CHOICES = (
        ('close', 'Cerrar plan'),
        ('recurrence', 'Registrar recurrencia'),
    )

    resultado = forms.ChoiceField(choices=RESULTADO_CHOICES)
    comentarios = forms.CharField(widget=Textarea, label='Comentarios', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_tailwind_widgets(self)


class EvidenciaForm(forms.ModelForm):
    class Meta:
        model = Evidencia
        exclude = [
            "user",
            "accion",
            "ejecucion",
        ]
        widgets = {
            "fecha": DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["archivo"].required = True

        apply_tailwind_widgets(self)
