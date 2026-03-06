from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from app.models import AppSettings

LOGGER = logging.getLogger(__name__)


class SettingsStore:
    def __init__(self, app_name: str = "Pripominacek") -> None:
        appdata = os.getenv("APPDATA")
        if appdata:
            self.base_dir = Path(appdata) / app_name
        else:
            self.base_dir = Path.home() / "AppData" / "Roaming" / app_name

        self.settings_path = self.base_dir / "settings.json"
        self.log_path = self.base_dir / "pripominacek.log"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        if not self.settings_path.exists():
            return AppSettings()

        try:
            raw = self.settings_path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("settings root must be object")
            return AppSettings.from_dict(payload)
        except Exception:
            LOGGER.exception("Nepodarilo se nacist nastaveni, pouziji se defaultni hodnoty.")
            return AppSettings()

    def save(self, settings: AppSettings) -> bool:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = self.settings_path.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(self.settings_path)
            return True
        except Exception:
            LOGGER.exception("Nepodarilo se ulozit nastaveni.")
            return False
