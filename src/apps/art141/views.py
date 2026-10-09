from django.views.generic import TemplateView

from apps.art141.services.indicadores import (
    get_anios_disponibles,
    get_desempeno_afectacion,
    get_distribucion_dias_afectacion,
    get_distribucion_sexo,
    get_piramide_edades,
    get_resumen_art141,
    get_sankey_distritos,
    get_tramites_por_mes,
)
from apps.art141.services.va import (
    get_distribucion_va_por_seccion,
    get_resumen_va,
    get_va_por_distrito,
    get_va_por_seccion,
)
from apps.art141.services.geografia import (
    get_georreferencia_va,
)


class DashboardArt141(TemplateView):
    template_name = "art141/dashboard_art141.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        anios = get_anios_disponibles()
        anio = self._get_anio(anios)

        context.update(
            {
                "anios": anios,
                "anio_seleccionado": anio,
                "resumen": get_resumen_art141(anio),
                "por_mes": get_tramites_por_mes(anio),
                "sexo": get_distribucion_sexo(anio),
                "piramide": get_piramide_edades(anio),
                "sankey": get_sankey_distritos(anio),
                "desempeno": get_desempeno_afectacion(anio),
                "distribucion_dias": (
                    get_distribucion_dias_afectacion(anio)
                ),
            }
        )

        return context

    def _get_anio(self, anios):
        valor = self.request.GET.get("anio")

        if not valor:
            return None

        try:
            anio = int(valor)
        except (TypeError, ValueError):
            return None

        if anio not in anios:
            return None

        return anio


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
