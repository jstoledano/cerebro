from django.views.generic import TemplateView


class KpiIndex(TemplateView):
    template_name = 'kpi/index.html'
