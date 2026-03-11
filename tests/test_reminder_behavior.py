from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from app.main_window import MainWindow
from app.models import Reminder
from app.reminder_dialog import ReminderPopupDialog
from app.scheduler import ReminderScheduler


class ReminderBehaviorTests(unittest.TestCase):
    def test_recent_past_once_reminder_stays_in_history(self) -> None:
        now = datetime(2026, 3, 11, 12, 0, 0)
        reminder = Reminder(
            id="past",
            time="08:00",
            text="Past",
            repeat="once",
            once_date="2026-03-10",
            enabled=False,
            created_at=(now - timedelta(days=5)).isoformat(timespec="seconds"),
        )

        self.assertTrue(ReminderScheduler.is_past_reminder(reminder, now))
        self.assertFalse(ReminderScheduler._should_delete_past_reminder(reminder, now))

    def test_past_reminder_older_than_30_days_is_deleted(self) -> None:
        now = datetime(2026, 3, 11, 12, 0, 0)
        reminder = Reminder(
            id="expired",
            time="08:00",
            text="Expired",
            repeat="once",
            once_date="2026-01-01",
            enabled=False,
            created_at=(now - timedelta(days=31)).isoformat(timespec="seconds"),
        )
        reminders = [reminder]
        scheduler = ReminderScheduler()
        scheduler._reminders = reminders

        changed = scheduler._cleanup_state(now)

        self.assertTrue(changed)
        self.assertEqual([], reminders)

    def test_daily_reminder_is_not_marked_as_past(self) -> None:
        now = datetime(2026, 3, 11, 12, 0, 0)
        reminder = Reminder(
            id="daily",
            time="09:00",
            text="Daily",
            repeat="daily",
            enabled=True,
        )

        self.assertFalse(ReminderScheduler.is_past_reminder(reminder, now))

    def test_snooze_updates_snooze_until(self) -> None:
        now = datetime(2026, 3, 11, 12, 0, 0)
        reminder = Reminder(id="1", time="12:00", text="Test")

        MainWindow.apply_popup_result(
            reminder,
            ReminderPopupDialog.RESULT_SNOOZE,
            now,
            snooze_minutes=15,
        )

        self.assertEqual("2026-03-11T12:15:00", reminder.snooze_until)
        self.assertTrue(reminder.enabled)

    def test_custom_time_changes_daily_time(self) -> None:
        now = datetime(2026, 3, 11, 12, 0, 0)
        reminder = Reminder(
            id="daily-custom",
            time="12:00",
            text="Test",
            repeat="daily",
            snooze_until="2026-03-11T12:15:00",
            last_fired_at="2026-03-11T12:00:00",
        )

        MainWindow.apply_popup_result(
            reminder,
            ReminderPopupDialog.RESULT_RESCHEDULE,
            now,
            custom_datetime=datetime(2026, 3, 11, 14, 30, 0),
        )

        self.assertEqual("14:30", reminder.time)
        self.assertIsNone(reminder.snooze_until)
        self.assertIsNone(reminder.last_fired_at)

    def test_custom_time_changes_once_time_and_date(self) -> None:
        now = datetime(2026, 3, 11, 12, 0, 0)
        reminder = Reminder(
            id="once-custom",
            time="12:00",
            text="Test",
            repeat="once",
            once_date="2026-03-11",
            enabled=False,
        )

        MainWindow.apply_popup_result(
            reminder,
            ReminderPopupDialog.RESULT_RESCHEDULE,
            now,
            custom_datetime=datetime(2026, 3, 12, 9, 45, 0),
        )

        self.assertEqual("09:45", reminder.time)
        self.assertEqual("2026-03-12", reminder.once_date)
        self.assertTrue(reminder.enabled)

    def test_done_disables_once_reminder(self) -> None:
        now = datetime(2026, 3, 11, 12, 0, 0)
        reminder = Reminder(
            id="done-once",
            time="12:00",
            text="Test",
            repeat="once",
            once_date="2026-03-11",
            enabled=True,
            snooze_until=(now + timedelta(minutes=5)).isoformat(timespec="seconds"),
        )

        MainWindow.apply_popup_result(reminder, ReminderPopupDialog.RESULT_DONE, now)

        self.assertFalse(reminder.enabled)
        self.assertIsNone(reminder.snooze_until)


if __name__ == "__main__":
    unittest.main()
