from __future__ import annotations

import logging
import sys
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - mimo Windows
    winreg = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "Pripominacek"
AUTOSTART_ARGUMENT = "--autostart"


class AutostartManager:
    def __init__(self, value_name: str = RUN_VALUE_NAME) -> None:
        self.value_name = value_name

    def is_supported(self) -> bool:
        return bool(winreg) and sys.platform.startswith("win")

    def build_command(self) -> str:
        if getattr(sys, "frozen", False):
            exe_path = Path(sys.executable).resolve()
            return f'"{exe_path}" {AUTOSTART_ARGUMENT}'

        python_exe = Path(sys.executable).resolve()
        main_script = (Path(__file__).resolve().parent / "main.py").resolve()
        return f'"{python_exe}" "{main_script}" {AUTOSTART_ARGUMENT}'

    def is_enabled(self) -> bool:
        current_command = self.get_command()
        return bool(current_command and current_command.strip())

    def get_command(self) -> str | None:
        if not self.is_supported():
            return None

        assert winreg is not None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, self.value_name)
            if isinstance(value, str):
                return value
            return None
        except FileNotFoundError:
            return None
        except OSError:
            LOGGER.exception("Nepodarilo se precist autostart z registru.")
            return None

    def is_current_command(self) -> bool:
        current_command = self.get_command()
        if not current_command:
            return False
        return current_command.strip() == self.build_command()

    def set_enabled(self, enabled: bool) -> bool:
        if not self.is_supported():
            return False

        assert winreg is not None
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY_PATH,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    winreg.SetValueEx(
                        key,
                        self.value_name,
                        0,
                        winreg.REG_SZ,
                        self.build_command(),
                    )
                else:
                    try:
                        winreg.DeleteValue(key, self.value_name)
                    except FileNotFoundError:
                        pass
            return True
        except OSError:
            LOGGER.exception("Nepodarilo se zapsat autostart do registru.")
            return False
