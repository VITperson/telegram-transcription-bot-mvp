from __future__ import annotations

import math


def minutes_to_debit(duration_sec: float) -> int:
    """Round seconds up to next full minute, minimum 1 for non-zero."""
    if duration_sec <= 0:
        return 0
    return max(1, math.ceil(duration_sec / 60.0))


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    if seconds < 0:
        seconds = 0
    total = int(math.floor(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

