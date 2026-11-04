from core.notification_schedule import CLAVES_AGENDA


def es_cabecera(user):
    profile = getattr(user, "profile", None)
    unit = profile.unidad_organizacional if profile else None
    return bool(user.is_active and unit and unit.activa and unit.clave in CLAVES_AGENDA)


def recibe_agenda(user):
    profile = getattr(user, "profile", None)
    return bool(user.is_active and (es_cabecera(user) or (profile and profile.recibe_notificaciones)))
