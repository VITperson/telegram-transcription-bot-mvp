from __future__ import annotations

import datetime as dt
from src.core.utils import format_timestamp


def build_md(title: str, link: str | None, language: str | None, segments: list[dict]) -> str:
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"_Generated: {dt.datetime.utcnow().isoformat()}_")
    if link:
        lines.append(f"\n**Source:** {link}")
    if language:
        lines.append(f"\n**Language:** {language}")
    lines.append("\n## Transcript\n")
    for seg in segments:
        start = format_timestamp(seg.get("start", 0))
        end = format_timestamp(seg.get("end", 0))
        lines.append(f"- [{start} - {end}] {seg.get('text','').strip()}")
    return "\n".join(lines)

