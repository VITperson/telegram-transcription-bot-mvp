from __future__ import annotations

import json
from pathlib import Path


def test_i18n_keys_match():
    en = json.loads(Path("i18n/en.json").read_text(encoding="utf-8"))
    ru = json.loads(Path("i18n/ru.json").read_text(encoding="utf-8"))
    assert set(en.keys()) == set(ru.keys())

