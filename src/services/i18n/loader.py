from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


class I18n:
    def __init__(self, base_path: str | None = None) -> None:
        self.base = Path(base_path or "i18n")
        self._data = {
            "en": self._load("en.json"),
            "ru": self._load("ru.json"),
        }

    def _load(self, filename: str) -> dict:
        with open(self.base / filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_translator(self, lang: str) -> Callable[[str], str]:
        d = self._data.get(lang) or self._data["en"]

        def _(key: str) -> str:
            return d.get(key, key)

        return _

