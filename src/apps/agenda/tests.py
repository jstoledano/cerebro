"""Pruebas de seleccion temporal; no requieren base de datos."""
from datetime import date

from django.test import SimpleTestCase

from apps.agenda.services.data import (
    attention_reason, dashboard_metrics, deadline_date, items_for_range,
    next_review_date, pending_tasks, priority_window, stamp_date,
    todo_items_for_day,
)


TODAY = date(2026, 11, 20)


def task(id_, scheduled="2026-10-01", deadline="2026-12-20", priority=None,
         state="TODO", properties=None):
    return {
        "kind": "task", "id": id_, "title": id_, "state": state,
        "priority": priority, "properties": properties or {},
        "scheduled": {"start": scheduled} if scheduled else None,
        "deadline": {"start": deadline} if deadline else None,
    }


class AgendaSelectionTests(SimpleTestCase):
    def test_dates_accept_iso(self):
        self.assertEqual(stamp_date({"start": "2026-11-20"}), TODAY)
        self.assertEqual(stamp_date({"start": "2026-11-20T10:00"}), TODAY)

    def test_only_todo_is_pending(self):
        payload = {"items": [task("A"), task("B", state="DONE"), task("C", state="DOING")]}
        self.assertEqual([x["id"] for x in pending_tasks(payload)], ["A"])

    def test_priority_windows(self):
        self.assertEqual([priority_window(task("X", priority=p)) for p in ("A", "B", "C", None)], [14, 7, 3, 1])

    def test_a_appears_fourteen_days_before_deadline(self):
        item = task("A", deadline="2026-12-04", priority="A")
        self.assertIsNotNone(attention_reason(item, TODAY))
        self.assertIsNone(attention_reason(item, TODAY - __import__("datetime").timedelta(days=1)))

    def test_b_appears_seven_days_before_deadline(self):
        self.assertIsNotNone(attention_reason(task("B", deadline="2026-11-27", priority="B"), TODAY))
        self.assertIsNone(attention_reason(task("B", deadline="2026-11-28", priority="B"), TODAY))

    def test_c_appears_three_days_before_deadline(self):
        self.assertIsNotNone(attention_reason(task("C", deadline="2026-11-23", priority="C"), TODAY))
        self.assertIsNone(attention_reason(task("C", deadline="2026-11-24", priority="C"), TODAY))

    def test_unprioritized_only_one_day_before_deadline(self):
        self.assertIsNotNone(attention_reason(task("X", deadline="2026-11-21"), TODAY))
        self.assertIsNone(attention_reason(task("X", deadline="2026-11-22"), TODAY))

    def test_long_running_unprioritized_does_not_fill_agenda(self):
        item = task("VA-010", scheduled="2026-10-01", deadline="2027-05-26")
        self.assertIsNone(attention_reason(item, TODAY))
        self.assertEqual(todo_items_for_day({"items": [item]}, TODAY), [])

    def test_aagg_is_selected_today(self):
        item = task("aagg-01", scheduled="2026-11-17", deadline="2026-11-23", priority="B")
        self.assertIsNotNone(attention_reason(item, TODAY))
        self.assertEqual([x["id"] for x in todo_items_for_day({"items": [item]}, TODAY)], ["aagg-01"])

    def test_included_on_scheduled_date(self):
        item = task("X", scheduled="2026-11-20", deadline="2027-05-31")
        self.assertEqual(attention_reason(item, TODAY), "Inicia")

    def test_expired_tasks_are_excluded_from_today(self):
        item = task("X", scheduled="2026-11-01", deadline="2026-11-19", priority="A")
        self.assertIsNone(attention_reason(item, TODAY))
        self.assertEqual(len(dashboard_metrics({"items": [item]}, TODAY)["overdue"]), 1)

    def test_radar_excludes_distant_long_running_tasks(self):
        payload = {"items": [
            task("LONG", deadline="2027-05-26"),
            task("DUE", deadline="2026-11-23"),
            task("START", scheduled="2026-11-25", deadline="2027-01-20"),
        ]}
        metrics = dashboard_metrics(payload, TODAY)
        self.assertEqual({x["id"] for x in metrics["upcoming"]}, {"DUE", "START"})

    def test_next_review_is_optional(self):
        item = task("X", properties={"NEXT_REVIEW": "2026-11-20"})
        self.assertEqual(next_review_date(item), TODAY)
        self.assertEqual(attention_reason(item, TODAY), "Revisar")

    def test_missed_review_stays_visible_until_updated(self):
        item = task("X", properties={"NEXT_REVIEW": "2026-11-19"})
        self.assertEqual(attention_reason(item, TODAY), "Revisar")

    def test_invalid_review_is_ignored(self):
        self.assertIsNone(next_review_date(task("X", properties={"NEXT_REVIEW": "pronto"})))

    def test_weekly_selected_once(self):
        item = task("aagg-01", scheduled="2026-11-17", deadline="2026-11-23", priority="B")
        payload = {"items": [item]}
        week1 = items_for_range(payload, date(2026, 11, 16), date(2026, 11, 22))
        week2 = items_for_range(payload, date(2026, 11, 23), date(2026, 11, 29))
        self.assertEqual(len(week1), 1)
        self.assertEqual(week1[0]["agenda_date"], "2026-11-17")
        self.assertEqual(len(week2), 1)
        self.assertEqual(week2[0]["agenda_date"], "2026-11-23")

    def test_no_weekly_repeat_of_long_running_unprioritized(self):
        item = task("VA-010", scheduled="2026-10-01", deadline="2027-05-26")
        self.assertEqual(items_for_range({"items": [item]}, date(2026, 11, 16), date(2026, 11, 22)), [])

    def test_same_day_schedule_and_deadline_is_single_occurrence(self):
        item = task("X", scheduled="2026-11-20", deadline="2026-11-20")
        results = items_for_range({"items": [item]}, TODAY, TODAY)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["date_kind"], "Programada/Vence")
