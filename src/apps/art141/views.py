from django.utils import timezone
from django.views.generic import TemplateView

from apps.art141.services.geografia import (
    get_georreferencia_va,
)
from apps.art141.services.indicadores import (
    get_anios_disponibles,
    get_desempeno_entrega,
    get_distribucion_dias_entrega,
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
                "entrega": get_desempeno_entrega(anio),
                "distribucion_entrega": (
                    get_distribucion_dias_entrega(anio)
                ),
            }
        )

        return context

    def _get_anio(self, anios):
        valor = self.request.GET.get("anio")

        if valor:
            try:
                anio = int(valor)
            except (TypeError, ValueError):
                anio = None

            if anio in anios:
                return anio

        anio_actual = timezone.localdate().year

        if anio_actual in anios:
            return anio_actual

        if anios:
            return anios[0]

        return None


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
