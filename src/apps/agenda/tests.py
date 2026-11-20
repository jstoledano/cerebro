from datetime import date
from django.test import SimpleTestCase

from apps.agenda.services.data import (
    active_items, dashboard_metrics, dated_occurrences, deadline_date,
    item_date, items_for_range, stamp_date,
)


class AgendaDataTests(SimpleTestCase):
    def test_stamp_date_date_only(self):
        self.assertEqual(stamp_date({"start": "2026-11-19"}), date(2026, 11, 19))

    def test_stamp_date_datetime(self):
        self.assertEqual(stamp_date({"start": "2026-11-19T10:00"}), date(2026, 11, 19))

    def test_item_date_prefers_scheduled(self):
        item = {"scheduled": {"start": "2026-11-19"}, "deadline": {"start": "2026-11-20"}}
        self.assertEqual(item_date(item), date(2026, 11, 19))

    def test_terminal_states_are_hidden_from_active_views(self):
        payload = {"items": [{"state": "TODO"}, {"state": "DONE"}, {"state": "CANCELLED"}]}
        self.assertEqual(len(active_items(payload)), 1)

    def test_same_day_schedule_and_deadline_are_one_occurrence(self):
        item = {"scheduled": {"start": "2026-11-19"}, "deadline": {"start": "2026-11-19"}}
        self.assertEqual(dated_occurrences(item), [(date(2026, 11, 19), "Programada/Vence")])

    def test_deadline_is_independent_from_scheduled(self):
        item = {"scheduled": {"start": "2026-11-25"}, "deadline": {"start": "2026-11-18"}}
        self.assertEqual(item_date(item), date(2026, 11, 25))
        self.assertEqual(deadline_date(item), date(2026, 11, 18))

    def test_items_for_range_duplicates_task_by_distinct_dates(self):
        item = {"kind": "task", "state": "TODO", "id": "T-1", "title": "Prueba",
                "scheduled": {"start": "2026-11-19"}, "deadline": {"start": "2026-11-20"}}
        result = items_for_range({"items": [item]}, date(2026, 11, 19), date(2026, 11, 20))
        self.assertEqual([entry["agenda_date"] for entry in result], ["2026-11-19", "2026-11-20"])

    def test_dashboard_overdue_uses_deadline_not_scheduled(self):
        payload = {"items": [{"kind": "task", "state": "TODO",
                              "scheduled": {"start": "2026-11-25"},
                              "deadline": {"start": "2026-11-18"}}]}
        metrics = dashboard_metrics(payload, date(2026, 11, 19))
        self.assertEqual(len(metrics["overdue"]), 1)
