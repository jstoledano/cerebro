from django import forms
from core.notification_schedule import DIAS
from apps.profiles.models import Profile
from .models import CalendarioNotificaciones


class AgendaCorreoForm(forms.ModelForm):
    recibe_notificaciones = forms.BooleanField(label="Recibir mi agenda diaria", required=False)

    class Meta:
        model = Profile
        fields = ["recibe_notificaciones"]


class CalendarioCorreoForm(forms.ModelForm):
    dias = forms.TypedMultipleChoiceField(
        label="Días de envío", choices=DIAS, coerce=int, widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = CalendarioNotificaciones
        fields = ["dias"]
