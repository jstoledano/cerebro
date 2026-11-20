"""Pruebas de seleccion temporal; no requieren base de datos."""
from datetime import date, timedelta

from django.test import SimpleTestCase

from apps.agenda.services.data import (
    attention_reason, dashboard_metrics, deadline_date, items_for_range,
    next_review_date, pending_tasks, priority_window, stamp_date,
    todo_items_for_day, week_bounds, weekly_overdue_items, weekly_radar_items,
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

    def test_dashboard_radar_matches_weekly_pdf_radar(self):
        payload = {"items": [
            task("LONG", deadline="2027-05-26"),
            task("DUE", scheduled="2026-11-17", deadline="2026-11-23"),
            task("START", scheduled="2026-11-25", deadline="2027-01-20"),
            task("S1", scheduled="2026-11-30", deadline="2026-12-15"),
            task("S2", scheduled="2026-12-01", deadline="2026-12-20"),
            task("S3", scheduled="2026-12-02", deadline="2026-12-21"),
            task("S4", scheduled="2026-12-03", deadline="2026-12-22"),
        ]}
        week_end = week_bounds(TODAY)[1]
        metrics = dashboard_metrics(payload, TODAY)
        pdf_radar = weekly_radar_items(payload, week_end, limit=5)
        self.assertEqual(
            [(x["id"], x["agenda_date"], x["date_kind"]) for x in metrics["upcoming"]],
            [(x["id"], x["agenda_date"], x["date_kind"]) for x in pdf_radar],
        )
        self.assertEqual(len(metrics["upcoming"]), 5)
        self.assertEqual(metrics["upcoming"][0]["id"], "DUE")

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


class WeeklyDocumentTests(SimpleTestCase):
    def test_week_is_monday_to_sunday_regardless_of_generation_day(self):
        for offset in range(7):
            self.assertEqual(
                week_bounds(date(2026, 11, 16) + timedelta(days=offset)),
                (date(2026, 11, 16), date(2026, 11, 22)),
            )

    def test_overdue_uses_generation_cutoff(self):
        p = {"items": [
            task("OLD", deadline="2026-11-19"),
            task("TODAY", deadline="2026-11-20"),
            task("DONE", deadline="2026-11-01", state="DONE"),
        ]}
        self.assertEqual([i["id"] for i in weekly_overdue_items(p, TODAY)], ["OLD"])

    def test_weekly_radar_starts_after_sunday_and_extends_as_needed(self):
        p = {"items": [
            task("PAST", scheduled="2026-11-18", deadline="2026-11-22"),
            task("DUE", scheduled="2026-11-17", deadline="2026-11-23"),
            task("START", scheduled="2026-11-30", deadline="2027-01-05"),
            task("DONE", scheduled="2026-11-23", state="DONE"),
        ]}
        result = weekly_radar_items(p, date(2026, 11, 22), limit=5)
        self.assertEqual([i["id"] for i in result], ["DUE", "START"])
        self.assertEqual([i["date_kind"] for i in result], ["Vence", "Inicia"])

    def test_radar_uses_one_milestone_per_activity(self):
        p = {"items": [task("X", scheduled="2026-11-23", deadline="2026-11-24")]}
        self.assertEqual(len(weekly_radar_items(p, date(2026, 11, 22))), 1)
        self.assertEqual(weekly_radar_items(p, date(2026, 11, 22))[0]["date_kind"], "Inicia")

    def test_radar_prefers_deadline_on_same_day(self):
        p = {"items": [task("X", scheduled="2026-11-23", deadline="2026-11-23")]}
        self.assertEqual(weekly_radar_items(p, date(2026, 11, 22))[0]["date_kind"], "Vence")


class WeeklyPDFCacheTests(SimpleTestCase):
    def test_one_filename_for_all_days_of_same_week(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from apps.agenda.services.weekly import weekly_pdf_path
        with TemporaryDirectory() as tmp:
            expected = Path(tmp) / "agenda-20261116-20261122.pdf"
            for offset in range(7):
                self.assertEqual(
                    weekly_pdf_path(date(2026, 11, 16) + timedelta(days=offset), tmp),
                    expected,
                )

    def test_existing_pdf_is_reused_without_regeneration(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from apps.agenda.services.weekly import get_or_create_weekly_pdf, weekly_pdf_path
        with TemporaryDirectory() as tmp:
            expected = weekly_pdf_path(TODAY, tmp)
            expected.write_bytes(b"%PDF-1.7\n" + b"x" * 140)
            with patch("apps.agenda.services.weekly.generate_pdf") as generate:
                actual = get_or_create_weekly_pdf(TODAY, output_dir=tmp)
            self.assertEqual(actual, expected)
            generate.assert_not_called()

    def test_missing_pdf_is_generated_once_and_then_reused(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from apps.agenda.services.weekly import get_or_create_weekly_pdf
        payload = {"items": [task("TEST", deadline="2026-11-23")]}
        def fake_generate(items, start, end, output_dir, **kwargs):
            result = Path(output_dir) / f"agenda-{start:%Y%m%d}-{end:%Y%m%d}.pdf"
            result.write_bytes(b"%PDF-1.7\n" + b"y" * 140)
            return result
        with TemporaryDirectory() as tmp:
            with patch("apps.agenda.services.weekly.generate_pdf", side_effect=fake_generate) as generate:
                p1 = get_or_create_weekly_pdf(TODAY, payload=payload, output_dir=tmp)
                p2 = get_or_create_weekly_pdf(TODAY, payload=payload, output_dir=tmp)
            self.assertEqual(p1, p2)
            self.assertEqual(generate.call_count, 1)

    def test_force_overwrites_existing_pdf(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from apps.agenda.services.weekly import get_or_create_weekly_pdf, weekly_pdf_path
        payload = {"items": []}
        def fake_generate(items, start, end, output_dir, **kwargs):
            result = Path(output_dir) / f"agenda-{start:%Y%m%d}-{end:%Y%m%d}.pdf"
            result.write_bytes(b"%PDF-1.7\n" + b"z" * 140)
            return result
        with TemporaryDirectory() as tmp:
            expected = weekly_pdf_path(TODAY, tmp)
            expected.write_bytes(b"%PDF-1.7\n" + b"x" * 140)
            with patch("apps.agenda.services.weekly.generate_pdf", side_effect=fake_generate) as generate:
                get_or_create_weekly_pdf(TODAY, payload=payload, output_dir=tmp, force=True)
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(expected.read_bytes(), b"%PDF-1.7\n" + b"z" * 140)
