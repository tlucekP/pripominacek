from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayController(QObject):
    open_requested = Signal()
    add_requested = Signal()
    pause_requested = Signal(bool)
    exit_requested = Signal()

    def __init__(self, icon: QIcon, parent=None) -> None:
        super().__init__(parent)
        self._paused = False

        self._tray = QSystemTrayIcon(icon, parent)
        self._tray.setToolTip("Připomínáček")

        menu = QMenu()
        self._open_action = menu.addAction("Otevřít")
        self._add_action = menu.addAction("Přidat připomínku")
        menu.addSeparator()
        self._pause_action = menu.addAction("Pozastavit vše")
        menu.addSeparator()
        self._exit_action = menu.addAction("Konec")

        self._tray.setContextMenu(menu)

        self._open_action.triggered.connect(self.open_requested.emit)
        self._add_action.triggered.connect(self.add_requested.emit)
        self._pause_action.triggered.connect(self._on_pause_toggle)
        self._exit_action.triggered.connect(self.exit_requested.emit)

        self._tray.activated.connect(self._on_activated)

    @staticmethod
    def is_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        self._pause_action.setText("Obnovit" if paused else "Pozastavit vše")

    def show_message(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _on_pause_toggle(self) -> None:
        self.pause_requested.emit(not self._paused)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_requested.emit()
