"""Representacion de fichas de tareas publicas."""
from apps.agenda.services.data import priority_label

# Lista explicita de propiedades publicables en el CMI.
PUBLIC_PROPERTIES = ('PLAN', 'SCOPE', 'REFERENCE', 'OWNER', 'OPERATIVE', 'MONITOR', 'NEXT_REVIEW')


def task_detail(item):
    props = item.get('properties') or {}
    return {
        'id': item.get('id') or '',
        'title': item.get('title') or '',
        'body': item.get('body') or '',
        'state': item.get('state') or '',
        'priority': priority_label(item),
        'scheduled': (item.get('scheduled') or {}).get('start') or '',
        'deadline': (item.get('deadline') or {}).get('start') or '',
        'closed': (item.get('closed') or {}).get('start') or '',
        'source': item.get('source') or '',
        'properties': {key: str(props[key]) for key in PUBLIC_PROPERTIES if props.get(key)},
    }
