from django.views.generic import TemplateView
from .models import KPI


class KpiIndex(TemplateView):
    template_name = 'kpi/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'KPI'
        context['kpi'] = KPI.objects.filter(active=True)
        return context
