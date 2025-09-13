from __future__ import annotations

import datetime as dt
from src.core.utils import format_timestamp


def build_txt(title: str, link: str | None, language: str | None, segments: list[dict]) -> str:
    lines = []
    lines.append(title)
    lines.append(dt.datetime.utcnow().isoformat())
    if link:
        lines.append(f"Source: {link}")
    if language:
        lines.append(f"Language: {language}")
    lines.append("")
    for seg in segments:
        start = format_timestamp(seg.get("start", 0))
        end = format_timestamp(seg.get("end", 0))
        lines.append(f"[{start} - {end}] {seg.get('text','').strip()}")
    return "\n".join(lines)

