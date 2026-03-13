from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QStyle

from app.autostart import AUTOSTART_ARGUMENT, AutostartManager
from app.main_window import MainWindow
from app.settings_store import SettingsStore
from app.theme import apply_theme
from app.tray import TrayController

LOGGER = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(AUTOSTART_ARGUMENT, dest="autostart", action="store_true")
    return parser.parse_known_args(argv)[0]


def configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    if not getattr(sys, "frozen", False):
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def load_app_icon(app: QApplication) -> QIcon:
    assets_dir = Path(__file__).resolve().parent / "assets"
    ico_path = assets_dir / "icon.ico"
    png_path = assets_dir / "icon.png"

    if ico_path.exists():
        return QIcon(str(ico_path))
    if png_path.exists():
        return QIcon(str(png_path))

    return app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)


def main() -> int:
    args = parse_args(sys.argv[1:])

    app = QApplication(sys.argv)
    app.setApplicationName("Pripominacek")
    app.setQuitOnLastWindowClosed(False)

    settings_store = SettingsStore()
    configure_logging(settings_store.log_path)

    settings = settings_store.load()
    apply_theme(app, settings.theme)

    app_icon = load_app_icon(app)
    app.setWindowIcon(app_icon)

    if not TrayController.is_available():
        QMessageBox.critical(None, "Připomínáček", "Systémová oznamovací oblast není dostupná.")
        return 1

    main_window = MainWindow(
        settings_store=settings_store,
        settings=settings,
        autostart_manager=AutostartManager(),
        app_icon=app_icon,
    )

    tray = TrayController(app_icon, app)
    tray.open_requested.connect(main_window.show_main_window)
    tray.add_requested.connect(main_window.open_add_dialog_from_tray)
    tray.pause_requested.connect(main_window.set_paused)
    tray.exit_requested.connect(main_window.quit_application)

    main_window.paused_changed.connect(tray.set_paused)
    main_window.attach_tray(tray)

    tray.set_paused(settings.paused)
    tray.show()

    if not args.autostart:
        main_window.show_main_window()

    exit_code = app.exec()
    tray.hide()
    LOGGER.info("Aplikace ukoncena s kodem %s", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
