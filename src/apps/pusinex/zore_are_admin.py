"""Admin separado para no alterar la administracion vigente de PUSINEX."""
from django.contrib import admin

from .zore_models import Are, Zore


class _PersonalRestringidoAdmin(admin.ModelAdmin):
    list_per_page = 30
    search_fields = ("numero",)

    def has_add_permission(self, request):
        return False  # Las asignaciones se incorporan por CSV.

    def has_delete_permission(self, request, obj=None):
        return False

    def _permite_personal(self, request):
        return request.user.has_perm("pusinex.ver_personal_zore_are")

    def get_readonly_fields(self, request, obj=None):
        return self.identificadores

    def get_fields(self, request, obj=None):
        campos = list(self.identificadores)
        if self._permite_personal(request):
            campos.extend(self.campos_personal)
        return campos


@admin.register(Zore)
class ZoreAdmin(_PersonalRestringidoAdmin):
    identificadores = ("distrito", "numero")
    campos_personal = ("supervisor_nombre", "supervisor_correo", "supervisor_telefono")
    list_display = ("distrito", "numero")
    list_filter = ("distrito",)


@admin.register(Are)
class AreAdmin(_PersonalRestringidoAdmin):
    identificadores = ("distrito", "zore", "numero")
    campos_personal = ("cae_nombre", "cae_correo", "cae_telefono")
    list_display = ("distrito", "zore", "numero")
    list_filter = ("distrito", "zore")
