from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QCloseEvent, QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.autostart import AutostartManager
from app.edit_dialog import EditReminderDialog
from app.models import AppSettings, Reminder, new_reminder_id
from app.reminder_dialog import ReminderPopupDialog
from app.scheduler import ReminderScheduler
from app.settings_store import SettingsStore
from app.theme import THEMES, apply_theme

THEME_OPTIONS = [
    ("Světlá", "light"),
    ("Tmavá", "dark"),
    ("Pastelová zelená", "pastel_green"),
    ("Pastelová červená", "pastel_red"),
    ("Pastelová žlutá", "pastel_yellow"),
]


class MainWindow(QMainWindow):
    paused_changed = Signal(bool)

    def __init__(
        self,
        settings_store: SettingsStore,
        settings: AppSettings,
        autostart_manager: AutostartManager,
        app_icon: QIcon,
    ) -> None:
        super().__init__()
        self._settings_store = settings_store
        self._settings = settings
        self._autostart = autostart_manager
        self._tray = None

        self._allow_close = False
        self._popup_open = False
        self._popup_queue: list[str] = []

        self.setWindowTitle("Připomínáček")
        self.setWindowIcon(app_icon)
        self.resize(860, 640)

        self._scheduler = ReminderScheduler(self)
        self._scheduler.reminder_due.connect(self._enqueue_popup)
        self._scheduler.reminders_changed.connect(self._on_scheduler_data_changed)
        self._scheduler.set_reminders(self._settings.reminders)
        self._scheduler.set_paused(self._settings.paused)

        self._build_ui()
        self._sync_initial_settings()
        self._refresh_tables()
        self._update_pause_label()

    def attach_tray(self, tray) -> None:
        self._tray = tray

    def show_main_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def open_add_dialog_from_tray(self) -> None:
        self.show_main_window()
        self.add_reminder()

    def quit_application(self) -> None:
        self._allow_close = True
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def set_paused(self, paused: bool) -> None:
        if self._settings.paused == paused:
            return

        self._settings.paused = paused
        self._scheduler.set_paused(paused)
        self.paused_changed.emit(paused)
        self._update_pause_label()
        self._save_settings()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._allow_close:
            event.accept()
            return

        event.ignore()
        self.hide()
        if self._tray is not None:
            self._tray.show_message("Připomínáček", "Aplikace běží na pozadí v oznamovací oblasti.")

    def add_reminder(self) -> None:
        dialog = EditReminderDialog(self)
        if dialog.exec() != EditReminderDialog.DialogCode.Accepted:
            return

        payload = dialog.payload()
        self._settings.reminders.append(
            Reminder(
                id=new_reminder_id(),
                time=str(payload["time"]),
                text=str(payload["text"]),
                enabled=bool(payload["enabled"]),
                repeat=str(payload["repeat"]),
                once_date=(str(payload["once_date"]) if payload["once_date"] else None),
            )
        )
        self._persist_and_reschedule()

    def edit_selected_reminder(self) -> None:
        reminder = self._selected_reminder()
        if reminder is None:
            QMessageBox.information(self, "Bez výběru", "Vyber připomínku, kterou chceš upravit.")
            return

        dialog = EditReminderDialog(self, reminder)
        if dialog.exec() != EditReminderDialog.DialogCode.Accepted:
            return

        payload = dialog.payload()
        reminder.time = str(payload["time"])
        reminder.text = str(payload["text"])
        reminder.repeat = str(payload["repeat"])
        reminder.once_date = str(payload["once_date"]) if payload["once_date"] else None
        reminder.enabled = bool(payload["enabled"])

        if reminder.repeat == "daily":
            reminder.once_date = None

        reminder.snooze_until = None
        reminder.last_fired_at = None

        self._persist_and_reschedule()

    def delete_selected_reminder(self) -> None:
        reminder = self._selected_reminder()
        if reminder is None:
            QMessageBox.information(self, "Bez výběru", "Vyber připomínku, kterou chceš smazat.")
            return

        confirm = QMessageBox.question(
            self,
            "Smazat připomínku",
            "Opravdu chceš vybranou připomínku smazat?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._settings.reminders = [item for item in self._settings.reminders if item.id != reminder.id]
        self._scheduler.set_reminders(self._settings.reminders)
        self._persist_and_reschedule()

    @staticmethod
    def apply_popup_result(
        reminder: Reminder,
        result_code: int,
        now: datetime,
        snooze_minutes: int | None = None,
        custom_datetime: datetime | None = None,
    ) -> None:
        if result_code == ReminderPopupDialog.RESULT_SNOOZE and snooze_minutes is not None:
            reminder.enabled = True
            reminder.snooze_until = (now + timedelta(minutes=snooze_minutes)).isoformat(timespec="seconds")
            return

        if result_code == ReminderPopupDialog.RESULT_RESCHEDULE and custom_datetime is not None:
            reminder.enabled = True
            reminder.snooze_until = None
            reminder.last_fired_at = None
            reminder.time = custom_datetime.strftime("%H:%M")
            if reminder.repeat == "once":
                reminder.once_date = custom_datetime.date().isoformat()
            return

        if reminder.repeat == "once":
            reminder.enabled = False
            reminder.snooze_until = None

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(12)

        title = QLabel("Připomínáček")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root_layout.addWidget(title)

        self._table = QTableWidget(0, 4, self)
        self._configure_active_table(self._table)
        root_layout.addWidget(self._table)

        button_row = QHBoxLayout()
        self._add_button = QPushButton("Přidat")
        self._edit_button = QPushButton("Upravit")
        self._delete_button = QPushButton("Smazat")

        self._edit_button.setObjectName("secondaryButton")
        self._delete_button.setObjectName("secondaryButton")

        self._add_button.clicked.connect(self.add_reminder)
        self._edit_button.clicked.connect(self.edit_selected_reminder)
        self._delete_button.clicked.connect(self.delete_selected_reminder)

        button_row.addWidget(self._add_button)
        button_row.addWidget(self._edit_button)
        button_row.addWidget(self._delete_button)
        button_row.addStretch(1)
        root_layout.addLayout(button_row)

        self._show_past_checkbox = QCheckBox("Zobrazit minulé připomínky")
        self._show_past_checkbox.toggled.connect(self._history_box_visibility_changed)
        root_layout.addWidget(self._show_past_checkbox)

        self._history_box = QGroupBox("Minulé připomínky")
        history_layout = QVBoxLayout(self._history_box)
        self._history_table = QTableWidget(0, 3, self)
        self._configure_history_table(self._history_table)
        history_layout.addWidget(self._history_table)
        self._history_box.setVisible(False)
        root_layout.addWidget(self._history_box)

        settings_box = QGroupBox("Nastavení")
        settings_layout = QVBoxLayout(settings_box)

        self._autostart_checkbox = QCheckBox("Spouštět po startu Windows")
        self._autostart_checkbox.toggled.connect(self._on_autostart_toggled)

        self._autostart_hint = QLabel(
            "Po zapnutí se vytvoří položka v registru HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run."
        )
        self._autostart_hint.setWordWrap(True)
        self._autostart_hint.setProperty("muted", True)

        theme_row = QHBoxLayout()
        theme_label = QLabel("Vzhled")
        self._theme_combo = QComboBox(self)
        for label, key in THEME_OPTIONS:
            self._theme_combo.addItem(label, key)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        theme_row.addWidget(theme_label)
        theme_row.addWidget(self._theme_combo)
        theme_row.addStretch(1)

        self._pause_label = QLabel()
        self._pause_label.setProperty("muted", True)

        settings_layout.addWidget(self._autostart_checkbox)
        settings_layout.addWidget(self._autostart_hint)
        settings_layout.addLayout(theme_row)
        settings_layout.addWidget(self._pause_label)
        root_layout.addWidget(settings_box)

        self.setCentralWidget(root)

    def _configure_active_table(self, table: QTableWidget) -> None:
        table.setHorizontalHeaderLabels(["Čas", "Text", "Opakování", "Zapnuto"])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.itemChanged.connect(self._on_table_item_changed)
        table.itemSelectionChanged.connect(lambda: self._clear_selection_on_other_table(self._history_table))

    def _configure_history_table(self, table: QTableWidget) -> None:
        table.setHorizontalHeaderLabels(["Čas", "Text", "Opakování"])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.itemSelectionChanged.connect(lambda: self._clear_selection_on_other_table(self._table))

    def _clear_selection_on_other_table(self, table: QTableWidget) -> None:
        sender = self.sender()
        if not isinstance(sender, QTableWidget) or sender.currentRow() < 0:
            return
        table.blockSignals(True)
        table.clearSelection()
        table.setCurrentCell(-1, -1)
        table.blockSignals(False)

    def _history_box_visibility_changed(self, checked: bool) -> None:
        self._history_box.setVisible(checked)

    def _sync_initial_settings(self) -> None:
        if self._autostart.is_supported():
            current_state = self._autostart.is_enabled()
            self._settings.autostart = current_state
            self._autostart_checkbox.blockSignals(True)
            self._autostart_checkbox.setChecked(current_state)
            self._autostart_checkbox.blockSignals(False)
        else:
            self._autostart_checkbox.setChecked(False)
            self._autostart_checkbox.setEnabled(False)
            self._autostart_hint.setText("Autostart je dostupný pouze na Windows.")

        saved_theme = self._settings.theme if self._settings.theme in THEMES else "light"
        self._settings.theme = saved_theme

        index = self._theme_combo.findData(saved_theme)
        if index < 0:
            index = 0
        self._theme_combo.blockSignals(True)
        self._theme_combo.setCurrentIndex(index)
        self._theme_combo.blockSignals(False)

    def _refresh_tables(self) -> None:
        self._populate_active_table(self._active_reminders())
        self._populate_history_table(self._past_reminders())

    def _populate_active_table(self, reminders: list[Reminder]) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)

        bold_font = QFont()
        bold_font.setBold(True)
        text_font = QFont(bold_font)
        text_font.setPointSize(16)

        for row, reminder in enumerate(reminders):
            self._table.insertRow(row)
            items = self._build_row_items(reminder)
            for column, item in enumerate(items):
                if item is not None:
                    item.setFont(text_font if column == 1 else bold_font)
                    self._table.setItem(row, column, item)

        self._table.blockSignals(False)

    def _populate_history_table(self, reminders: list[Reminder]) -> None:
        self._history_table.blockSignals(True)
        self._history_table.setRowCount(0)

        base_font = QFont()
        base_font.setBold(False)
        base_font.setStrikeOut(True)
        text_font = QFont(base_font)
        text_font.setPointSize(16)
        red_brush = QBrush(QColor("#b00020"))

        for row, reminder in enumerate(reminders):
            self._history_table.insertRow(row)
            items = self._build_row_items(reminder, include_enabled=False)
            for column, item in enumerate(items):
                if item is None:
                    continue
                item.setForeground(red_brush)
                item.setFont(text_font if column == 1 else base_font)
                self._history_table.setItem(row, column, item)

        self._history_table.blockSignals(False)

    def _build_row_items(self, reminder: Reminder, include_enabled: bool = True) -> list[QTableWidgetItem | None]:
        time_item = QTableWidgetItem(reminder.time)
        time_item.setData(Qt.ItemDataRole.UserRole, reminder.id)
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        text_item = QTableWidgetItem(self._short_text(reminder.text))
        text_item.setToolTip(reminder.text)
        text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        repeat_label = "Jednorázově" if reminder.repeat == "once" else "Denně"
        repeat_item = QTableWidgetItem(repeat_label)
        repeat_item.setFlags(repeat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        items: list[QTableWidgetItem | None] = [time_item, text_item, repeat_item]

        if include_enabled:
            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            enabled_item.setCheckState(
                Qt.CheckState.Checked if reminder.enabled else Qt.CheckState.Unchecked
            )
            items.append(enabled_item)

        return items

    def _active_reminders(self) -> list[Reminder]:
        now = datetime.now()
        return [
            reminder
            for reminder in self._settings.reminders
            if not ReminderScheduler.is_past_reminder(reminder, now)
        ]

    def _past_reminders(self) -> list[Reminder]:
        now = datetime.now()
        return [
            reminder
            for reminder in self._settings.reminders
            if ReminderScheduler.is_past_reminder(reminder, now)
        ]

    @staticmethod
    def _short_text(raw: str, limit: int = 70) -> str:
        compact = " ".join(raw.split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 1]}…"

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 3:
            return

        row = item.row()
        id_item = self._table.item(row, 0)
        if id_item is None:
            return

        reminder_id = id_item.data(Qt.ItemDataRole.UserRole)
        if not reminder_id:
            return

        reminder = self._find_reminder_by_id(str(reminder_id))
        if reminder is None:
            return

        reminder.enabled = item.checkState() == Qt.CheckState.Checked
        if not reminder.enabled:
            reminder.snooze_until = None
        self._persist_and_reschedule(refresh_tables=False)

    def _on_autostart_toggled(self, checked: bool) -> None:
        if not self._autostart.is_supported():
            return

        success = self._autostart.set_enabled(checked)
        if not success:
            QMessageBox.warning(
                self,
                "Autostart",
                "Nepodařilo se změnit autostart v registru.",
            )
            self._autostart_checkbox.blockSignals(True)
            self._autostart_checkbox.setChecked(not checked)
            self._autostart_checkbox.blockSignals(False)
            return

        self._settings.autostart = checked
        self._save_settings()

    def _on_theme_changed(self, _index: int) -> None:
        selected_key = str(self._theme_combo.currentData())
        app = QApplication.instance()
        if app is not None:
            selected_key = apply_theme(app, selected_key)
        self._settings.theme = selected_key
        self._save_settings()

    def _enqueue_popup(self, reminder_id: str) -> None:
        self._popup_queue.append(reminder_id)
        self._show_next_popup()

    def _show_next_popup(self) -> None:
        if self._popup_open or not self._popup_queue:
            return

        reminder_id = self._popup_queue.pop(0)
        reminder = self._find_reminder_by_id(reminder_id)
        if reminder is None:
            QTimer.singleShot(0, self._show_next_popup)
            return

        self._popup_open = True
        dialog = ReminderPopupDialog(reminder, None)
        result = dialog.exec()

        now = datetime.now()
        self.apply_popup_result(
            reminder,
            result,
            now,
            snooze_minutes=dialog.snooze_minutes(),
            custom_datetime=dialog.custom_datetime(),
        )

        self._popup_open = False
        self._persist_and_reschedule()
        QTimer.singleShot(0, self._show_next_popup)

    def _on_scheduler_data_changed(self) -> None:
        self._save_settings()
        self._refresh_tables()

    def _persist_and_reschedule(self, refresh_tables: bool = True) -> None:
        if refresh_tables:
            self._refresh_tables()
        self._save_settings()
        self._scheduler.reschedule()

    def _save_settings(self) -> None:
        self._settings_store.save(self._settings)

    def _selected_reminder(self) -> Reminder | None:
        reminder = self._selected_reminder_from_table(self._table)
        if reminder is not None:
            return reminder
        return self._selected_reminder_from_table(self._history_table)

    def _selected_reminder_from_table(self, table: QTableWidget) -> Reminder | None:
        row = table.currentRow()
        if row < 0:
            return None
        id_item = table.item(row, 0)
        if id_item is None:
            return None
        reminder_id = id_item.data(Qt.ItemDataRole.UserRole)
        if not reminder_id:
            return None
        return self._find_reminder_by_id(str(reminder_id))

    def _find_reminder_by_id(self, reminder_id: str) -> Reminder | None:
        for reminder in self._settings.reminders:
            if reminder.id == reminder_id:
                return reminder
        return None

    def _update_pause_label(self) -> None:
        self._pause_label.setText(
            "Plánovač je pozastavený." if self._settings.paused else "Plánovač je aktivní."
        )
