from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal
import uuid

RepeatType = Literal["once", "daily"]

VALID_REPEATS = {"once", "daily"}
VALID_THEMES = {
    "light",
    "dark",
    "pastel_green",
    "pastel_red",
    "pastel_yellow",
}


def new_reminder_id() -> str:
    return str(uuid.uuid4())


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _normalize_datetime(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = parse_iso_datetime(value.strip())
    if parsed is None:
        return None
    return parsed.isoformat(timespec="seconds")


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def _is_valid_time_string(value: str) -> bool:
    try:
        datetime.strptime(value, "%H:%M")
        return True
    except ValueError:
        return False


def _is_valid_date_string(value: str | None) -> bool:
    if not value:
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


@dataclass(slots=True)
class Reminder:
    id: str
    time: str = "09:00"
    text: str = ""
    enabled: bool = True
    repeat: RepeatType = "daily"
    once_date: str | None = None
    snooze_until: str | None = None
    last_fired_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reminder":
        reminder_id = _as_str(data.get("id")).strip() or new_reminder_id()

        time_value = _as_str(data.get("time"), "09:00").strip()
        if not _is_valid_time_string(time_value):
            time_value = "09:00"

        repeat_value = _as_str(data.get("repeat"), "daily").strip().lower()
        if repeat_value not in VALID_REPEATS:
            repeat_value = "daily"

        once_date: str | None = _as_str(data.get("once_date")).strip() or None
        if repeat_value == "once":
            if not _is_valid_date_string(once_date):
                once_date = datetime.now().date().isoformat()
        else:
            once_date = None

        return cls(
            id=reminder_id,
            time=time_value,
            text=_as_str(data.get("text")).strip(),
            enabled=_as_bool(data.get("enabled"), True),
            repeat=repeat_value,  # type: ignore[arg-type]
            once_date=once_date,
            snooze_until=_normalize_datetime(data.get("snooze_until")),
            last_fired_at=_normalize_datetime(data.get("last_fired_at")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "time": self.time,
            "text": self.text,
            "enabled": self.enabled,
            "repeat": self.repeat,
            "once_date": self.once_date if self.repeat == "once" else None,
            "snooze_until": self.snooze_until,
            "last_fired_at": self.last_fired_at,
        }
        return payload


@dataclass(slots=True)
class AppSettings:
    reminders: list[Reminder] = field(default_factory=list)
    autostart: bool = False
    paused: bool = False
    theme: str = "light"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        reminder_payload = data.get("reminders", [])
        reminders: list[Reminder] = []
        if isinstance(reminder_payload, list):
            for item in reminder_payload:
                if isinstance(item, dict):
                    reminders.append(Reminder.from_dict(item))

        theme = _as_str(data.get("theme"), "light").strip()
        if theme not in VALID_THEMES:
            theme = "light"

        return cls(
            reminders=reminders,
            autostart=_as_bool(data.get("autostart"), False),
            paused=_as_bool(data.get("paused"), False),
            theme=theme,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reminders": [reminder.to_dict() for reminder in self.reminders],
            "autostart": self.autostart,
            "paused": self.paused,
            "theme": self.theme,
        }
