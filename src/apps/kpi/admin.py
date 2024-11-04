"""Gestión de la aplicación KPI en el panel de administración de Django."""

from django.contrib import admin
from django.contrib.admin import TabularInline

from .models import KPI, Record, Period


# noinspection PyUnusedLocal
class RecordInline(TabularInline):
    """Genera los formularios inline para guardar registros en un periodo."""
    exclude = (
        'user',
        'cumulative_value',
        'percentage_of_nominal',
        'cumulative_percentage'
    )
    model = Record
    extra = 1

    @staticmethod
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:
                instance.user = request.user
            instance.save()
        formset.save_m2m()


class PeriodInline(TabularInline):
    exclude = ('user',)
    model = Period
    extra = 1

    @staticmethod
    def save_formset(request, formset):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.user = request.user
            instance.save()
        formset.save_m2m()


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ('kpi', 'period', 'start', 'end', 'target', 'nominal', 'active')
    search_fields = ('kpi__name', 'period')
    list_filter = ('kpi', 'active')
    ordering = ('kpi', 'period')
    inlines = [RecordInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.user = request.user
            instance.save()
        formset.save_m2m()


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    exclude = ('user',)
    list_display = ('name', 'kpi_type', 'active')
    search_fields = ('name', 'description')
    list_filter = ('kpi_type', 'active')
    ordering = ('pos',)
    inlines = [PeriodInline]

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        for formset in formsets:
            for obj in formset.save(commit=False):
                if not obj.pk:
                    obj.user = request.user
                obj.save()


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    exclude = ('user',)
    list_display = ('period', 'date', 'value')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)
