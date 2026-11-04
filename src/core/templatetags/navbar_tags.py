"""Datos de presentación de la sesión, sin modificar el perfil."""

from django import template
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


@register.simple_tag
def navbar_identity(user):
    if not user.is_authenticated:
        return {}

    name = user.get_full_name().strip() or user.get_username()
    try:
        initials = (user.profile.siglas or "").strip()
    except ObjectDoesNotExist:
        initials = ""

    if not initials:
        parts = name.split()
        initials = "".join(part[0] for part in parts[:2])

    return {"name": name, "initials": initials.upper()[:4] or "?"}
