from __future__ import annotations

import logging
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

from app.models import Reminder, parse_iso_datetime

LOGGER = logging.getLogger(__name__)


class ReminderScheduler(QObject):
    reminder_due = Signal(str)
    reminders_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._reminders: list[Reminder] = []
        self._paused = False

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    def set_reminders(self, reminders: list[Reminder]) -> None:
        self._reminders = reminders
        self.reschedule()

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        self.reschedule()

    def reschedule(self) -> None:
        self._timer.stop()

        now = datetime.now()
        changed = self._cleanup_state(now)
        if changed:
            self.reminders_changed.emit()

        if self._paused:
            return

        nearest: datetime | None = None
        for reminder in self._reminders:
            if not reminder.enabled:
                continue

            candidate = self._next_trigger(reminder, now)
            if candidate is None:
                continue

            if nearest is None or candidate < nearest:
                nearest = candidate

        if nearest is None:
            return

        delay_ms = max(0, int((nearest - now).total_seconds() * 1000))
        delay_ms = min(delay_ms, 2_147_000_000)
        self._timer.start(delay_ms)

    def _on_timeout(self) -> None:
        now = datetime.now()
        changed = False
        due_ids: list[str] = []

        for reminder in self._reminders:
            if not reminder.enabled:
                continue
            if not self._is_due(reminder, now):
                continue
            if self._already_fired_this_minute(reminder, now):
                continue

            reminder.last_fired_at = now.isoformat(timespec="seconds")
            if reminder.snooze_until is not None:
                reminder.snooze_until = None

            due_ids.append(reminder.id)
            changed = True

        if self._cleanup_state(now):
            changed = True

        if changed:
            self.reminders_changed.emit()

        for reminder_id in due_ids:
            self.reminder_due.emit(reminder_id)

        self.reschedule()

    def _next_trigger(self, reminder: Reminder, now: datetime) -> datetime | None:
        snooze_at = parse_iso_datetime(reminder.snooze_until)
        if snooze_at:
            return snooze_at

        due_time = self._parse_time(reminder.time)
        if due_time is None:
            LOGGER.warning("Reminder %s ma neplatny cas '%s'.", reminder.id, reminder.time)
            return None

        if reminder.repeat == "daily":
            candidate = datetime.combine(now.date(), due_time)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        due_at = self._once_due_datetime(reminder)
        if due_at is None:
            return None
        if due_at <= now:
            return None
        return due_at

    def _is_due(self, reminder: Reminder, now: datetime) -> bool:
        snooze_at = parse_iso_datetime(reminder.snooze_until)
        if snooze_at is not None:
            return now >= snooze_at and not self._already_fired_after(reminder, snooze_at)

        due_time = self._parse_time(reminder.time)
        if due_time is None:
            return False

        if reminder.repeat == "daily":
            today_due = datetime.combine(now.date(), due_time)
            return (
                today_due <= now < today_due + timedelta(minutes=1)
                and not self._already_fired_after(reminder, today_due)
            )

        due_at = self._once_due_datetime(reminder)
        if due_at is None:
            return False

        return (
            due_at <= now < due_at + timedelta(minutes=1)
            and not self._already_fired_after(reminder, due_at)
        )

    def _cleanup_state(self, now: datetime) -> bool:
        changed = False

        for reminder in self._reminders:
            if reminder.snooze_until and parse_iso_datetime(reminder.snooze_until) is None:
                reminder.snooze_until = None
                changed = True

            if not reminder.enabled or reminder.repeat != "once":
                continue

            due_at = self._once_due_datetime(reminder)
            if due_at is None:
                reminder.enabled = False
                reminder.snooze_until = None
                changed = True
                continue

            fired_at = parse_iso_datetime(reminder.last_fired_at)
            if fired_at and fired_at >= due_at and reminder.snooze_until is None:
                reminder.enabled = False
                changed = True
                continue

            if reminder.snooze_until is None and now > due_at + timedelta(minutes=1):
                reminder.enabled = False
                changed = True

        return changed

    @staticmethod
    def _parse_time(raw_value: str):
        try:
            return datetime.strptime(raw_value, "%H:%M").time()
        except ValueError:
            return None

    @staticmethod
    def _once_due_datetime(reminder: Reminder) -> datetime | None:
        if not reminder.once_date:
            return None

        due_time = ReminderScheduler._parse_time(reminder.time)
        if due_time is None:
            return None

        try:
            due_date = datetime.strptime(reminder.once_date, "%Y-%m-%d").date()
        except ValueError:
            return None

        return datetime.combine(due_date, due_time)

    @staticmethod
    def _already_fired_after(reminder: Reminder, marker: datetime) -> bool:
        fired_at = parse_iso_datetime(reminder.last_fired_at)
        return bool(fired_at and fired_at >= marker)

    @staticmethod
    def _already_fired_this_minute(reminder: Reminder, now: datetime) -> bool:
        fired_at = parse_iso_datetime(reminder.last_fired_at)
        if fired_at is None:
            return False

        return (
            fired_at.year == now.year
            and fired_at.month == now.month
            and fired_at.day == now.day
            and fired_at.hour == now.hour
            and fired_at.minute == now.minute
        )
