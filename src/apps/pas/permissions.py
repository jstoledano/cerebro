"""Alcance de evidencias por actividad y supervisión funcional."""
from django.db.models import Q
from django.contrib.auth import get_user_model
from apps.profiles.models import UnidadOrganizacional
from .models import Ejecucion, Plan


def obtener_claves_normativas_agenda(
    perfil,
):
    """
    Devuelve las claves organizacionales cuya
    responsabilidad normativa debe ser visible
    en la agenda del perfil.

    Regla:

    - Un usuario ve su propia unidad y sus
      descendientes.
    - Si pertenece a una unidad cabecera de Junta
      Local de dos dígitos terminada en 0, también
      supervisa funcionalmente los capítulos
      equivalentes de las juntas distritales.

    Ejemplo para la unidad 50:

        50
        5010
        5020
        5030
        5040
        5050
        5099

        51
        5110
        5199

        52
        5210
        5299

        53
        5310
        5399
    """

    if (
        not perfil
        or not perfil.unidad_organizacional_id
    ):
        return set()

    unidad = perfil.unidad_organizacional
    if not unidad.activa:
        return set()

    unidades = {
        item.clave
        for item
        in unidad.obtener_descendientes(
            incluir_self=True
        )
    }

    clave = unidad.clave

    # ------------------------------------------------------
    # Cabecera funcional de Junta Local.
    #
    # Ejemplo:
    #
    # 50 -> 50, 51, 52, 53 y sus descendientes.
    # 20 -> 20, 21, 22, 23 y sus descendientes.
    # ------------------------------------------------------

    if (
        unidad.site == 0
        and len(clave) == 2
        and clave.endswith("0")
    ):
        prefijo_funcional = (
            clave[0]
        )

        unidades_equivalentes = (
            UnidadOrganizacional.objects
            .filter(
                activa=True,
                clave__in=[
                    f"{prefijo_funcional}0",
                    f"{prefijo_funcional}1",
                    f"{prefijo_funcional}2",
                    f"{prefijo_funcional}3",
                ],
            )
            .order_by(
                "clave"
            )
        )

        for unidad_equivalente in (
            unidades_equivalentes
        ):
            for item in (
                unidad_equivalente
                .obtener_descendientes(
                    incluir_self=True
                )
            ):
                unidades.add(
                    item.clave
                )

    return unidades


def filtro_normativo(user):
    claves = obtener_claves_normativas_agenda(getattr(user, "profile", None))
    perfil = getattr(user, "profile", None)
    propia = perfil.unidad_organizacional.clave if perfil and perfil.unidad_organizacional_id else None
    subordinadas = claves - {propia}
    return (
        Q(ciclo__accion__puesto_responsable__in=claves)
        | Q(responsable__is_active=True,
            responsable__profile__unidad_organizacional__activa=True,
            responsable__profile__unidad_organizacional__clave__in=subordinadas) & ~Q(responsable=user)
    )


def es_normativo_ejecucion(user, execution):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return Ejecucion.objects.filter(pk=execution.pk).filter(filtro_normativo(user)).exists()


def ejecuciones_gestionables(user):
    if not user or not user.is_authenticated or not user.is_active:
        return Ejecucion.objects.none()
    queryset = Ejecucion.objects.filter(
        ciclo__accion__plan__in=Plan.objects.visible_to(user)
    )
    if user.is_superuser:
        return queryset
    return queryset.filter(Q(responsable=user) | filtro_normativo(user)).distinct()


def usuario_puede_gestionar_evidencia(user, execution, operacion):
    if operacion not in {"crear", "editar", "eliminar"}:
        return False
    return ejecuciones_gestionables(user).filter(pk=execution.pk).exists()



def usuarios_supervisados(user):
    claves = obtener_claves_normativas_agenda(getattr(user, "profile", None))
    perfil = getattr(user, "profile", None)
    if perfil and perfil.unidad_organizacional_id:
        claves.discard(perfil.unidad_organizacional.clave)
    return get_user_model().objects.filter(is_active=True).filter(
        Q(pk=user.pk) | Q(profile__unidad_organizacional__clave__in=claves,
                         profile__unidad_organizacional__activa=True)
    ).select_related("profile", "profile__unidad_organizacional").order_by(
        "profile__unidad_organizacional__clave", "profile__order", "first_name", "last_name", "username",
    )
