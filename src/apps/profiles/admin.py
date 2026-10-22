# coding: utf-8

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from apps.profiles.models import (
    Profile,
    UnidadOrganizacional,
)


@admin.register(UnidadOrganizacional)
class UnidadOrganizacionalAdmin(admin.ModelAdmin):
    list_display = (
        "clave",
        "nombre",
        "site",
        "superior",
        "activa",
    )

    list_filter = (
        "site",
        "activa",
    )

    search_fields = (
        "clave",
        "nombre",
    )

    ordering = (
        "clave",
    )

    autocomplete_fields = (
        "superior",
    )


admin.site.unregister(User)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Perfil"
    fk_name = "user"

    fields = (
        "state",
        "site",
        "position",
        "unidad_organizacional",
        "order",
        "recibe_notificaciones",
    )

    autocomplete_fields = (
        "unidad_organizacional",
    )


class ProfileAdmin(UserAdmin):
    inlines = (
        ProfileInline,
    )

    list_display = (
        "username",
        "email",
        "get_site",
        "get_position",
        "get_unidad_organizacional",
        "is_staff",
    )

    list_select_related = (
        "profile",
        "profile__unidad_organizacional",
    )

    list_filter = (
        "profile__site",
        "profile__position",
        "profile__unidad_organizacional",
    )

    icon = (
        '<i class="material-icons">'
        "face"
        "</i>"
    )

    def get_inline_instances(
        self,
        request,
        obj=None,
    ):
        if not obj:
            return []

        return super().get_inline_instances(
            request,
            obj,
        )

    @admin.display(
        description="Sede",
    )
    def get_site(
        self,
        user,
    ):
        return (
            user.profile
            .get_site_display()
        )

    @admin.display(
        description="Puesto",
    )
    def get_position(
        self,
        user,
    ):
        return (
            user.profile
            .get_position_display()
        )

    @admin.display(
        description="Unidad organizacional",
    )
    def get_unidad_organizacional(
        self,
        user,
    ):
        return (
            user.profile
            .unidad_organizacional
            or "—"
        )


admin.site.register(
    User,
    ProfileAdmin,
)
