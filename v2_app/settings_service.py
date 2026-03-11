from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QSettings


class SettingsService:
    def __init__(self) -> None:
        self._settings = QSettings("LOGOPLANET", "PNGAssetStudioV2")

    def load_string(self, key: str, default: str = "") -> str:
        value = self._settings.value(key, default)
        return str(value) if value is not None else default

    def save_string(self, key: str, value: str) -> None:
        self._settings.setValue(key, value)

    def load_scope_keys(self) -> set[str]:
        raw = self._settings.value("scope_keys", [])
        if isinstance(raw, str):
            return {raw}
        return {str(item) for item in raw}

    def save_scope_keys(self, values: Iterable[str]) -> None:
        self._settings.setValue("scope_keys", list(values))

    def load_mockups_enabled(self, default: bool = True) -> bool:
        value = self._settings.value("include_mockups", default, type=bool)
        return bool(value)

    def save_mockups_enabled(self, enabled: bool) -> None:
        self._settings.setValue("include_mockups", enabled)

