from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout


class ReminderPopupDialog(QDialog):
    RESULT_DONE = 1
    RESULT_SNOOZE = 2

    def __init__(self, text: str, reminder_time: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Připomínáček")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        headline = QLabel("Je čas na připomínku")
        headline.setStyleSheet("font-size: 16px; font-weight: 700;")

        time_label = QLabel(f"Plánovaný čas: {reminder_time}")
        time_label.setProperty("muted", True)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        done_button = QPushButton("Hotovo")
        snooze_button = QPushButton("Odložit 10 min")
        snooze_button.setObjectName("secondaryButton")

        done_button.clicked.connect(lambda: self.done(self.RESULT_DONE))
        snooze_button.clicked.connect(lambda: self.done(self.RESULT_SNOOZE))

        button_layout = QHBoxLayout()
        button_layout.addWidget(done_button)
        button_layout.addWidget(snooze_button)

        layout = QVBoxLayout(self)
        layout.addWidget(headline)
        layout.addWidget(time_label)
        layout.addWidget(body)
        layout.addLayout(button_layout)

    def reject(self) -> None:
        self.done(self.RESULT_DONE)
