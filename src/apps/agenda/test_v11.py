"""Pruebas de las reglas de la iteracion 1.1 (sin base de datos)."""
from datetime import date
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.contrib.auth.models import AnonymousUser

from apps.agenda.services.indicators import project_indicators
from apps.agenda.services.tasks import task_detail
from apps.agenda.views import TaskDetailView, TaskStateView


def sample(id_, plan='VA', state='TODO', deadline='2026-11-22'):
    return {'kind':'task','id':id_,'title':'Titulo breve','body':'Explicacion extensa',
            'state':state, 'properties':{'PLAN':plan,'OWNER':'VRL','SECRET':'oculto'},
            'deadline':{'start':deadline}}


class IndicatorTests(SimpleTestCase):
    def test_percentage_and_overdue(self):
        payload = {'items':[sample('1'),sample('2',state='DONE'),sample('3',plan='VPPP')]}
        result = project_indicators(payload,date(2026,11,23))
        self.assertEqual((result[0]['total'],result[0]['done'],result[0]['overdue'],result[0]['percentage']), (2,1,1,50.0))
        self.assertEqual(result[1]['pending'],1)

    def test_detail_public_allowlist(self):
        detail = task_detail(sample('1'))
        self.assertEqual(detail['body'],'Explicacion extensa')
        self.assertNotIn('SECRET',detail['properties'])

    def test_public_detail(self):
        request = RequestFactory().get('/agenda/tarea/detalle/',{'id':'1'})
        request.user = AnonymousUser()
        with patch('apps.agenda.views._payload_or_error',return_value=({'items':[sample('1')]},None)):
            result = TaskDetailView.as_view()(request)
        self.assertEqual(result.status_code,200)
        self.assertIn(b'"can_edit": false',result.content)

    def test_anonymous_write_is_rejected(self):
        request = RequestFactory().post('/agenda/tarea/estado/',data='{"id":"1","state":"DONE","note":"Terminado"}',content_type='application/json')
        request.user = AnonymousUser()
        result = TaskStateView.as_view()(request)
        self.assertEqual(result.status_code,401)
