"""Indicadores de avance por proyecto calculados de la exportacion Org."""
from datetime import date
from apps.agenda.services.data import stamp_date


def project_indicators(payload, today: date):
    results = []
    for code, label in (("VA", "Voto Anticipado"), ("VPPP", "Voto de Personas en Prision Preventiva")):
        entries = [item for item in payload.get('items', [])
                   if item.get('kind') == 'task' and
                   str((item.get('properties') or {}).get('PLAN') or '').strip().upper() == code]
        done = sum(str(x.get('state') or '').upper() == 'DONE' for x in entries)
        cancelled = sum(str(x.get('state') or '').upper() in {'CANCELLED', 'CANCELED', 'OMITTED', 'OMITED'} for x in entries)
        pending = sum(str(x.get('state') or '').upper() == 'TODO' for x in entries)
        overdue = sum(str(x.get('state') or '').upper() == 'TODO' and
                      (stamp_date(x.get('deadline')) or date.max) < today for x in entries)
        denominator = len(entries) - cancelled
        results.append({'code': code, 'label': label, 'total': denominator, 'done': done,
                        'pending': pending, 'overdue': overdue, 'excluded': cancelled,
                        'percentage': round(done * 100 / denominator, 1) if denominator else 0})
    return results
