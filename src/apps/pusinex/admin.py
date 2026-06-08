from django.contrib import admin
from .models import Entidad, Distrito, DistritoLocal, Municipio, Seccion, Pusinex


class PusinexInline(admin.TabularInline):
    model = Pusinex
    extra = 1


class SeccionAdmin(admin.ModelAdmin):
    ordering = ["distrito", "municipio", "seccion"]
    list_filter = ["distrito", "municipio"]
    inlines = [PusinexInline]

    def save_formset(self, request, form, formset, change):
        # Evitar guardar en la base de datos inmediatamente
        instances = formset.save(commit=False)

        for instance in instances:
            # Validar que la instancia sea de tipo Pusinex
            if isinstance(instance, Pusinex):
                # Asignar el usuario si no tiene uno
                if not instance.user_id:
                    instance.user = request.user
            instance.save()

        # Manejar las instancias eliminadas desde el inline
        for obj in formset.deleted_objects:
            obj.delete()

        # Guardar relaciones ManyToMany si existen
        formset.save_m2m()


admin.site.register(Entidad)
admin.site.register(Distrito)
admin.site.register(DistritoLocal)
admin.site.register(Municipio)
admin.site.register(Seccion, SeccionAdmin)
