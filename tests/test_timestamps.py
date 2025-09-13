from __future__ import annotations

from src.core.utils import format_timestamp


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(5) == "00:00:05"
    assert format_timestamp(60) == "01:00:00".replace("01", "00").replace("00:00", "00:01")  # 00:01:00
    assert format_timestamp(3661) == "01:01:01"

