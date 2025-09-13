from __future__ import annotations

from src.core.utils import minutes_to_debit


def test_minutes_rounding():
    assert minutes_to_debit(0) == 0
    assert minutes_to_debit(1) == 1
    assert minutes_to_debit(59) == 1
    assert minutes_to_debit(60) == 1
    assert minutes_to_debit(61) == 2
    assert minutes_to_debit(120) == 2
    assert minutes_to_debit(121) == 3

