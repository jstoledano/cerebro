import html

from django.utils.html import strip_tags
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
from apps.profiles.models import (
    UnidadOrganizacional,
)
from .models import (
    Plan,
    Accion,
    Evidencia,
    AMBITO,
    CNC,
    PERIODICIDAD_CONTINUA,
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
        label="Otra fuente",
        required=False,
        widget=forms.TextInput(
            attrs={
                "disabled": "disabled",
            }
        ),
    )

    class Meta:
        model = Plan

        fields = [
            "documento",
            "nombre",
            "folio",
            "fecha_llenado",
            "descripcion",
            "fecha_inicio",
            "fecha_termino",
            "documento_fuente",

            # Campos específicos de CNC
            "tipo",
            "fuente",
            "otra_fuente",
            "correccion",
            "analisis",
            "evidencia_analisis",
        ]

        widgets = {
            "descripcion": forms.Textarea(
                attrs={
                    "rows": 5,
                }
            ),

            "fecha_llenado": DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                },
            ),

            "fecha_inicio": DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                },
            ),

            "fecha_termino": DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                },
            ),
        }

        labels = {
            "documento": "Tipo",
            "fecha_llenado": "Fecha de registro",
            "documento_fuente": "Documento fuente",
            "analisis": "Análisis de causa raíz",
            "evidencia_analisis": (
                "Archivo del análisis de causa raíz"
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "fecha_llenado"
        ].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields[
            "fecha_inicio"
        ].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields[
            "fecha_termino"
        ].input_formats = [
            "%Y-%m-%d",
        ]

        apply_tailwind_widgets(
            self
        )

    def clean(self):
        cleaned_data = (
            super().clean()
        )

        documento = (
            cleaned_data.get(
                "documento"
            )
        )

        fecha_inicio = (
            cleaned_data.get(
                "fecha_inicio"
            )
        )

        fecha_termino = (
            cleaned_data.get(
                "fecha_termino"
            )
        )

        if (
            fecha_inicio
            and fecha_termino
            and fecha_inicio > fecha_termino
        ):
            self.add_error(
                "fecha_termino",
                (
                    "La fecha de término no puede ser "
                    "anterior a la fecha de inicio."
                ),
            )

        if documento == CNC:
            fuente = (
                cleaned_data.get(
                    "fuente"
                )
            )

            otra_fuente = (
                cleaned_data.get(
                    "otra_fuente"
                )
            )

            if (
                fuente == 9
                and not otra_fuente
            ):
                self.add_error(
                    "otra_fuente",
                    (
                        "Este campo es obligatorio "
                        "si seleccionó Otros."
                    ),
                )

        return cleaned_data

    def save(
        self,
        commit=True,
    ):
        plan = super().save(
            commit=False
        )

        if plan.documento != CNC:
            plan.tipo = None
            plan.fuente = None
            plan.otra_fuente = None
            plan.correccion = ""
            plan.analisis = ""
            plan.evidencia_analisis = None

        if commit:
            plan.save()
            self.save_m2m()

        return plan


class AccionForm(forms.ModelForm):
    puesto_responsable = forms.ChoiceField(
        required=False,
        label="Responsable normativo",
        choices=(),
        help_text=(
            "Unidad o puesto que tiene la responsabilidad "
            "institucional de la actividad conforme al "
            "documento fuente. Puede coexistir con un "
            "responsable operativo."
        ),
    )
    responsable = ResponsableChoiceField(
        queryset=User.objects.order_by(
            "first_name",
            "last_name",
            "email",
        ),
        required=False,
        label="Responsable operativo",
        help_text=(
            "Persona responsable operativa de ejecutar "
            "la actividad cuando la asignación no se "
            "determina por puesto y ámbito."
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
            "recursos",
        ]

        labels = {
            "accion": "Descripción de la actividad",
            "puesto_responsable": "Responsable normativo",
            "recursos": "Recursos",
            "periodicidad": "Periodicidad",
            "formato_evidencia": "Formato de evidencia",
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de término",
            "evidencia": "Evidencia esperada",
            "prioridad": "Prioridad",
        }

        widgets = {
            "accion": forms.Textarea(
                attrs={
                    "rows": 5,
                }
            ),
            "fecha_inicio": DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                },
            ),
            "fecha_fin": DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                },
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )
        if self.instance and self.instance.pk and self.instance.accion:
            self.initial["accion"] = html.unescape(
                strip_tags(self.instance.accion)
            ).strip()

        unidades_responsables = UnidadOrganizacional.objects.filter(
            activa=True,
            clave__in=[
                "00",
                "10",
                "20",
                "30",
                "50",
                "51",
                "52",
                "53",
                "5010",
                "5020",
                "5030",
                "5040",
                "5050",
            ],
        ).order_by("clave")

        self.fields["puesto_responsable"].choices = [
            (
                "",
                "Sin responsable normativo",
            ),
            *[
                (
                    unidad.clave,
                    unidad.nombre_funcional,
                )
                for unidad in unidades_responsables
            ],
        ]

        self.fields["responsable"].empty_label = "Sin responsable operativo"

        self.fields["fecha_inicio"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["fecha_fin"].input_formats = [
            "%Y-%m-%d",
        ]

        if self.instance and self.instance.pk:
            self.fields["ambitos"].initial = self.instance.ambitos or []

        apply_tailwind_widgets(self)

    def clean(self):
        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get("fecha_inicio")

        fecha_fin = cleaned_data.get("fecha_fin")

        periodicidad = cleaned_data.get("periodicidad")

        # ======================================================
        # Fechas
        # ======================================================

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            self.add_error(
                "fecha_fin",
                ("La fecha de término no puede ser anterior a la fecha de inicio."),
            )

        # ------------------------------------------------------
        # Continua siempre representa un intervalo.
        # ------------------------------------------------------

        if periodicidad == PERIODICIDAD_CONTINUA:
            if not fecha_inicio:
                self.add_error(
                    "fecha_inicio",
                    ("Una actividad continua debe tener fecha de inicio."),
                )

            if not fecha_fin:
                self.add_error(
                    "fecha_fin",
                    ("Una actividad continua debe tener fecha de término."),
                )

        # ======================================================
        # Ámbitos
        # ======================================================

        ambitos = cleaned_data.get("ambitos") or []

        cleaned_data["ambitos"] = list(ambitos)

        puesto_responsable = cleaned_data.get("puesto_responsable")

        responsable = cleaned_data.get("responsable")

        # ======================================================
        # Responsabilidad
        #
        # Normativo y operativo pueden coexistir.
        #
        # Cuando existen varios ámbitos necesitamos una unidad
        # normativa que permita resolver las equivalencias por
        # Junta Local / Distrital.
        # ======================================================

        if len(ambitos) > 1 and not puesto_responsable:
            self.add_error(
                "puesto_responsable",
                (
                    "Para una actividad con varios "
                    "ámbitos selecciona el responsable "
                    "normativo."
                ),
            )

        if len(ambitos) <= 1 and not puesto_responsable and not responsable:
            self.add_error(
                "responsable",
                ("Selecciona un responsable operativo o un responsable normativo."),
            )

        # ======================================================
        # Creación
        # ======================================================

        if not self.instance.pk:
            return cleaned_data

        # ======================================================
        # Edición
        #
        # Si cambia la estructura de ejecución y ya existen
        # evidencias, no modificamos retrospectivamente los
        # ciclos a los que esas evidencias pertenecen.
        # ======================================================

        original = Accion.objects.get(pk=self.instance.pk)

        estructura_modificada = any(
            [
                (original.periodicidad != periodicidad),
                (set(original.ambitos or []) != set(ambitos)),
                (original.fecha_inicio != fecha_inicio),
                (original.fecha_fin != fecha_fin),
                (original.formato_evidencia != cleaned_data.get("formato_evidencia")),
                (original.puesto_responsable != puesto_responsable),
                (original.responsable_id != (responsable.pk if responsable else None)),
            ]
        )

        if not estructura_modificada:
            return cleaned_data

        tiene_evidencias = Evidencia.objects.filter(
            ejecucion__ciclo__accion=(original)
        ).exists()

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
