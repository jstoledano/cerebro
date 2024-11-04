import unittest
from django.test import TestCase, RequestFactory
from django.urls import reverse
from .views import KpiIndex
from .models import KPI


class KpiIndexTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kpi = KPI.objects.create(name='Test KPI', active=True)

    def test_get_context_data(self):
        request = self.factory.get(reverse('kpi:index'))
        view = KpiIndex.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('title', response.context_data)
        self.assertEqual(response.context_data['title'], 'KPI')
        self.assertIn('kpi', response.context_data)
        self.assertTrue(response.context_data['kpi'].filter(name='Test KPI').exists())


if __name__ == '__main__':
    unittest.main()
