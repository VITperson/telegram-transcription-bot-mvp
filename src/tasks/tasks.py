from __future__ import annotations

import json
from typing import Any
from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from src.tasks.celery_app import app
from src.services.media import youtube_download_to_wav, normalize_to_wav, cleanup_temp_file
from src.services.summarize import SummarizationProvider
from src.services.exports.txt import build_txt
from src.services.exports.md import build_md
from src.db.session import get_session
from src.db.models import Job, User, JobExport
from src.core.utils import minutes_to_debit


async def _with_session() -> AsyncSession:
    agen = get_session()
    return await agen.__anext__()


async def _create_job(user_id: int, source: dict[str, Any], language: str, mode: str) -> int:
    session = await _with_session()
    try:
        job = Job(user_id=user_id, source_type=source["type"], source_link=source.get("link"), mode=mode, language=language, status="queued")
        session.add(job)
        await session.commit()
        return job.id
    finally:
        await session.close()


async def enqueue_transcription_job(user_id: int, source: dict[str, Any], language: str, mode: str) -> None:
    job_id = await _create_job(user_id, source, language, mode)
    app.send_task("src.tasks.tasks.process_job", kwargs={"job_id": job_id, "source": source, "language": language, "mode": mode})


@shared_task(name="src.tasks.tasks.process_job")
def process_job(job_id: int, source: dict[str, Any], language: str, mode: str) -> None:
    wav_path: str | None = None
    try:
        if source["type"] == "youtube":
            wav_path, duration = youtube_download_to_wav(source["link"])  # type: ignore[index]
        else:
            # In a real bot we would download via Telegram API; here we assume an existing path/placeholder
            # TODO: integrate Telegram file download using bot token
            raise NotImplementedError("Telegram media download not implemented in worker")

        # Lazy import to avoid loading heavy deps at module import time
        from src.services.transcription import transcribe
        text, segments, file_duration = transcribe(wav_path, language)
        if not duration:
            duration = file_duration

        if mode == "summary":
            provider = SummarizationProvider()
            summary = provider.summarize(text, "summary", language=None if language == "auto" else language)
            key_points = None
        elif mode == "keypoints":
            provider = SummarizationProvider()
            summary = None
            key_points = provider.summarize(text, "keypoints", language=None if language == "auto" else language)
        else:
            summary = None
            key_points = None

        title = f"Job #{job_id}"
        txt_content = build_txt(title, source.get("link"), language, segments)
        md_content = build_md(title, source.get("link"), language, segments)

        # Persist results
        asyncio.run(_persist_results(job_id, text, segments, summary, key_points, duration, txt_content, md_content))
    finally:
        if wav_path:
            cleanup_temp_file(wav_path)


async def _persist_results(
    job_id: int,
    text: str,
    segments: list[dict[str, Any]],
    summary: Any,
    key_points: Any,
    duration: float,
    txt_content: str,
    md_content: str,
) -> None:
    session = await _with_session()
    try:
        res = await session.execute(select(Job).where(Job.id == job_id))
        job = res.scalar_one()
        job.transcript_text = text
        job.timestamps_json = segments
        job.summary_text = summary if isinstance(summary, str) else None
        job.key_points_json = key_points if isinstance(key_points, list) else None
        job.duration_sec = duration
        job.status = "completed"
        session.add(job)
        session.add_all([
            JobExport(job_id=job_id, kind="txt", content=txt_content),
            JobExport(job_id=job_id, kind="md", content=md_content),
        ])
        await session.commit()
    finally:
        await session.close()
