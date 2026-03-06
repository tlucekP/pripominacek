from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
)

from app.models import Reminder


class EditReminderDialog(QDialog):
    def __init__(self, parent=None, reminder: Reminder | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Připomínka")
        self.setModal(True)
        self.resize(420, 360)

        self._time_edit = QTimeEdit(self)
        self._time_edit.setDisplayFormat("HH:mm")

        self._text_edit = QTextEdit(self)
        self._text_edit.setPlaceholderText("Text připomínky")

        self._repeat_combo = QComboBox(self)
        self._repeat_combo.addItem("Jednorázově", "once")
        self._repeat_combo.addItem("Denně", "daily")

        self._date_label = QLabel("Datum", self)
        self._date_edit = QDateEdit(self)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDate(QDate.currentDate())

        self._enabled_checkbox = QCheckBox("Zapnuto", self)
        self._enabled_checkbox.setChecked(True)

        form_layout = QFormLayout()
        form_layout.addRow("Čas", self._time_edit)
        form_layout.addRow("Text", self._text_edit)
        form_layout.addRow("Opakování", self._repeat_combo)
        form_layout.addRow(self._date_label, self._date_edit)
        form_layout.addRow("", self._enabled_checkbox)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

        self._repeat_combo.currentIndexChanged.connect(self._update_once_visibility)

        if reminder:
            self._load_reminder(reminder)
        else:
            now_time = QTime.currentTime()
            self._time_edit.setTime(QTime(now_time.hour(), now_time.minute()))

        self._update_once_visibility()

    def _load_reminder(self, reminder: Reminder) -> None:
        reminder_time = QTime.fromString(reminder.time, "HH:mm")
        if reminder_time.isValid():
            self._time_edit.setTime(reminder_time)

        self._text_edit.setPlainText(reminder.text)

        repeat_index = self._repeat_combo.findData(reminder.repeat)
        if repeat_index >= 0:
            self._repeat_combo.setCurrentIndex(repeat_index)

        if reminder.once_date:
            try:
                parsed = date.fromisoformat(reminder.once_date)
                self._date_edit.setDate(QDate(parsed.year, parsed.month, parsed.day))
            except ValueError:
                self._date_edit.setDate(QDate.currentDate())

        self._enabled_checkbox.setChecked(reminder.enabled)

    def _update_once_visibility(self) -> None:
        is_once = self.current_repeat() == "once"
        self._date_label.setVisible(is_once)
        self._date_edit.setVisible(is_once)

    def current_repeat(self) -> str:
        data = self._repeat_combo.currentData()
        return str(data) if data else "daily"

    def payload(self) -> dict[str, object]:
        selected_time = self._time_edit.time()
        selected_date = self._date_edit.date()
        return {
            "time": f"{selected_time.hour():02d}:{selected_time.minute():02d}",
            "text": self._text_edit.toPlainText().strip(),
            "repeat": self.current_repeat(),
            "once_date": selected_date.toString("yyyy-MM-dd") if self.current_repeat() == "once" else None,
            "enabled": self._enabled_checkbox.isChecked(),
        }

    def accept(self) -> None:
        text = self._text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chybí text", "Vyplň text připomínky.")
            return

        if self.current_repeat() == "once" and not self._date_edit.date().isValid():
            QMessageBox.warning(self, "Chybí datum", "Vyber datum pro jednorázovou připomínku.")
            return

        super().accept()
