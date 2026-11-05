"""Días de envío en la zona horaria institucional (lunes=0)."""
from django.core.exceptions import ValidationError

CLAVES_AGENDA = ("00", "10", "20", "30", "50")
DIAS = tuple(enumerate(("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")))


def dias_laborables():
    return [0, 1, 2, 3, 4]


def validar_dias(value):
    if (not isinstance(value, list) or not value
            or any(type(day) is not int or day not in range(7) for day in value)
            or len(value) != len(set(value))):
        raise ValidationError("Seleccione al menos un día válido, sin repeticiones.")
