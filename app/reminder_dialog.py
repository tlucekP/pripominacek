from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)

from app.models import Reminder


class CustomReminderTimeDialog(QDialog):
    def __init__(self, reminder: Reminder, parent=None) -> None:
        super().__init__(parent)
        self._reminder = reminder
        self._selected_datetime: datetime | None = None

        self.setWindowTitle("Nastavit nový čas")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Zadej nový čas připomínky."))

        self._date_edit: QDateEdit | None = None
        if reminder.repeat == "once":
            date_label = QLabel("Datum")
            self._date_edit = QDateEdit(self)
            self._date_edit.setDisplayFormat("yyyy-MM-dd")
            self._date_edit.setCalendarPopup(True)
            if reminder.once_date:
                selected_date = QDate.fromString(reminder.once_date, "yyyy-MM-dd")
                self._date_edit.setDate(selected_date if selected_date.isValid() else QDate.currentDate())
            else:
                self._date_edit.setDate(QDate.currentDate())
            layout.addWidget(date_label)
            layout.addWidget(self._date_edit)

        current_time = QTime.fromString(reminder.time, "HH:mm")
        if not current_time.isValid():
            current_time = QTime.currentTime()

        time_label = QLabel("Čas")
        self._time_edit = QTimeEdit(self)
        self._time_edit.setDisplayFormat("HH:mm")
        self._time_edit.setTime(QTime(current_time.hour(), current_time.minute()))
        layout.addWidget(time_label)
        layout.addWidget(self._time_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_datetime(self) -> datetime | None:
        return self._selected_datetime

    def accept(self) -> None:
        selected_time = self._time_edit.time()
        selected_date = self._date_edit.date() if self._date_edit is not None else QDate.currentDate()
        candidate = datetime(
            selected_date.year(),
            selected_date.month(),
            selected_date.day(),
            selected_time.hour(),
            selected_time.minute(),
        )

        if self._reminder.repeat == "once" and candidate <= datetime.now():
            QMessageBox.warning(self, "Neplatný čas", "Pro jednorázovou připomínku vyber budoucí datum a čas.")
            return

        self._selected_datetime = candidate
        super().accept()


class ReminderPopupDialog(QDialog):
    RESULT_DONE = 1
    RESULT_SNOOZE = 2
    RESULT_RESCHEDULE = 3

    def __init__(self, reminder: Reminder, parent=None) -> None:
        super().__init__(parent)
        self._reminder = reminder
        self._snooze_minutes: int | None = None
        self._custom_datetime: datetime | None = None

        self.setWindowTitle("Připomínáček")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        headline = QLabel("Je čas na připomínku")
        headline.setStyleSheet("font-size: 16px; font-weight: 700;")

        time_label = QLabel(f"Plánovaný čas: {reminder.time}")
        time_label.setProperty("muted", True)

        body = QLabel(reminder.text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet("font-size: 16px; font-weight: 700;")

        done_button = QPushButton("Hotovo")
        done_button.clicked.connect(lambda: self.done(self.RESULT_DONE))

        snooze_grid = QGridLayout()
        snooze_options = [
            ("5 min", 5),
            ("15 min", 15),
            ("30 min", 30),
            ("1 hodina", 60),
        ]
        for index, (label, minutes) in enumerate(snooze_options):
            button = QPushButton(label)
            button.setObjectName("secondaryButton")
            button.clicked.connect(lambda _checked=False, value=minutes: self._finish_snooze(value))
            snooze_grid.addWidget(button, index // 2, index % 2)

        custom_button = QPushButton("Vlastní čas")
        custom_button.setObjectName("secondaryButton")
        custom_button.clicked.connect(self._choose_custom_time)

        button_layout = QHBoxLayout()
        button_layout.addWidget(done_button)
        button_layout.addWidget(custom_button)

        layout = QVBoxLayout(self)
        layout.addWidget(headline)
        layout.addWidget(time_label)
        layout.addWidget(body)
        layout.addLayout(snooze_grid)
        layout.addLayout(button_layout)

    def snooze_minutes(self) -> int | None:
        return self._snooze_minutes

    def custom_datetime(self) -> datetime | None:
        return self._custom_datetime

    def _finish_snooze(self, minutes: int) -> None:
        self._snooze_minutes = minutes
        self.done(self.RESULT_SNOOZE)

    def _choose_custom_time(self) -> None:
        dialog = CustomReminderTimeDialog(self._reminder, self)
        if dialog.exec() != CustomReminderTimeDialog.DialogCode.Accepted:
            return
        self._custom_datetime = dialog.selected_datetime()
        if self._custom_datetime is None:
            return
        self.done(self.RESULT_RESCHEDULE)

    def reject(self) -> None:
        self.done(self.RESULT_DONE)
