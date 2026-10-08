from django.views.generic import TemplateView

from apps.art141.services.geografia import (
    get_art141_por_distrito,
    get_georreferencia_art141,
    get_georreferencia_va,
)
from apps.art141.services.indicadores import (
    get_resumen_art141,
    get_tramites_por_anio,
)
from apps.art141.services.va import (
    get_distribucion_va_por_seccion,
    get_resumen_va,
    get_va_por_distrito,
    get_va_por_seccion,
)


class DashboardArt141(TemplateView):
    template_name = "art141/dashboard_art141.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["resumen"] = get_resumen_art141()
        context["por_anio"] = get_tramites_por_anio()
        context["por_distrito"] = get_art141_por_distrito()
        context["georreferencia"] = (
            get_georreferencia_art141()
        )

        return context


class DashboardVA(TemplateView):
    template_name = "art141/dashboard_va.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["resumen"] = get_resumen_va()
        context["por_distrito"] = get_va_por_distrito()
        context["por_seccion"] = get_va_por_seccion()
        context["distribucion_seccion"] = (
            get_distribucion_va_por_seccion()
        )
        context["georreferencia"] = (
            get_georreferencia_va()
        )

        return context
