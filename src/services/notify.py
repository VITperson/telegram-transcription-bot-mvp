from __future__ import annotations

from typing import Optional, Sequence
from aiogram import Bot
from aiogram.types import BufferedInputFile
from src.core.config import get_settings
from src.core.utils import format_timestamp


async def notify_user_transcription_ready(
    *,
    user_id: int,
    job_id: int,
    source_link: Optional[str],
    language: Optional[str],
    mode: str,
    duration_sec: float,
    transcript_text: str,
    summary_text: Optional[str],
    key_points: Optional[Sequence[str]],
    txt_content: str,
    md_content: str,
) -> None:
    settings = get_settings()
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    try:
        parts: list[str] = []
        parts.append(f"✅ Transcription ready (Job #{job_id})")
        if source_link:
            parts.append(f"Source: {source_link}")
        if language:
            parts.append(f"Language: {language}")
        parts.append(f"Duration: {format_timestamp(duration_sec)}")
        parts.append(f"Mode: {mode}")

        # Add a human-friendly preview depending on mode
        if summary_text and mode == "summary":
            preview = summary_text.strip()
            if len(preview) > 1500:
                preview = preview[:1500].rstrip() + "…"
            parts.append("\nSummary:\n" + preview)
        elif key_points and mode == "keypoints":
            bullets = list(key_points)[:10]
            formatted = "\n".join(f"• {p}" for p in bullets)
            parts.append("\nKey points:\n" + formatted)
        else:
            # Full transcript preview (first N chars)
            snippet = (transcript_text or "").strip()
            if snippet:
                if len(snippet) > 800:
                    snippet = snippet[:800].rstrip() + "…"
                parts.append("\nPreview:\n" + snippet)

        message_text = "\n".join(parts)
        await bot.send_message(chat_id=user_id, text=message_text)

        # Attach TXT and Markdown exports as files
        txt_file = BufferedInputFile(txt_content.encode("utf-8"), filename=f"transcript_{job_id}.txt")
        md_file = BufferedInputFile(md_content.encode("utf-8"), filename=f"transcript_{job_id}.md")
        await bot.send_document(chat_id=user_id, document=txt_file, caption="TXT transcript")
        await bot.send_document(chat_id=user_id, document=md_file, caption="Markdown transcript")
    finally:
        await bot.session.close()


async def notify_user_transcription_failed(*, user_id: int, job_id: int, reason: str | None = None) -> None:
    settings = get_settings()
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    try:
        hint = ""
        if reason:
            r = reason.strip()
            if len(r) > 200:
                r = r[:200].rstrip() + "…"
            hint = f"\n\nReason: {r}"
        text = (
            f"❌ Transcription failed (Job #{job_id}).\n"
            f"Please try again later or send a different file/link.{hint}"
        )
        await bot.send_message(chat_id=user_id, text=text)
    finally:
        await bot.session.close()
