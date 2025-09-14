from __future__ import annotations

import json
from typing import Any
import logging
from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from src.tasks.celery_app import app
from src.services.media import youtube_download_to_wav, normalize_to_wav, cleanup_temp_file
from src.services.summarize import SummarizationProvider
from src.services.exports.txt import build_txt
from src.services.exports.md import build_md
from src.db.session import SessionLocal
from src.db.models import Job, User, JobExport
from src.core.utils import minutes_to_debit

log = logging.getLogger("worker")


async def _create_job(user_id: int, source: dict[str, Any], language: str, mode: str) -> int:
    async with SessionLocal() as session:
        job = Job(user_id=user_id, source_type=source["type"], source_link=source.get("link"), mode=mode, language=language, status="queued")
        session.add(job)
        await session.commit()
        return job.id


async def _set_job_status(job_id: int, status: str) -> None:
    async with SessionLocal() as session:
        await session.execute(update(Job).where(Job.id == job_id).values(status=status))
        await session.commit()


async def enqueue_transcription_job(user_id: int, source: dict[str, Any], language: str, mode: str) -> None:
    job_id = await _create_job(user_id, source, language, mode)
    app.send_task("src.tasks.tasks.process_job", kwargs={"job_id": job_id, "source": source, "language": language, "mode": mode})


@shared_task(name="src.tasks.tasks.process_job", soft_time_limit=900, time_limit=960)
def process_job(job_id: int, source: dict[str, Any], language: str, mode: str) -> None:
    wav_path: str | None = None
    try:
        # mark job as processing
        try:
            asyncio.run(_set_job_status(job_id, "processing"))
        except Exception:
            pass
        if source["type"] == "youtube":
            wav_path, duration = youtube_download_to_wav(source["link"])  # type: ignore[index]
        else:
            # In a real bot we would download via Telegram API; here we assume an existing path/placeholder
            # TODO: integrate Telegram file download using bot token
            raise NotImplementedError("Telegram media download not implemented in worker")

        log.info("transcribe.start", extra={"job_id": job_id, "language": language, "mode": mode})
        # Lazy import to avoid loading heavy deps at module import time
        from src.services.transcription import transcribe
        text, segments, file_duration = transcribe(wav_path, language)
        log.info("transcribe.done", extra={"job_id": job_id, "duration": file_duration, "segments": len(segments)})
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
        log.info("job.completed", extra={"job_id": job_id})
    except Exception:
        try:
            asyncio.run(_set_job_status(job_id, "failed"))
        except Exception:
            pass
        log.exception("job.failed", extra={"job_id": job_id})
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
    async with SessionLocal() as session:
        res = await session.execute(select(Job).where(Job.id == job_id))
        job = res.scalar_one()
        job.transcript_text = text
        job.timestamps_json = segments
        job.summary_text = summary if isinstance(summary, str) else None
        job.key_points_json = key_points if isinstance(key_points, list) else None
        job.duration_sec = duration
        job.status = "completed"
        job.export_ready = True
        session.add(job)
        session.add_all([
            JobExport(job_id=job_id, kind="txt", content=txt_content),
            JobExport(job_id=job_id, kind="md", content=md_content),
        ])
        await session.commit()
