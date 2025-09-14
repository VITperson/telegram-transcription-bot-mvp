from __future__ import annotations

from typing import Any
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from src.core.config import get_settings


# Local (faster-whisper) model cache
_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from faster_whisper import WhisperModel  # import lazily to avoid loading in OpenAI mode
        settings = get_settings()
        _local_model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
            cpu_threads=max(1, int(settings.CPU_THREADS)),
            num_workers=max(1, int(settings.TRANSCRIBE_WORKERS)),
        )
    return _local_model


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _transcribe_local(wav_path: str, language: str | None) -> tuple[str, list[dict[str, Any]], float]:
    model = _get_local_model()
    segments, info = model.transcribe(wav_path, language=None if language == "auto" else language)
    out_segments: list[dict[str, Any]] = []
    texts = []
    for seg in segments:
        out_segments.append({
            "id": seg.id,
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        })
        texts.append(seg.text)
    return " ".join(texts).strip(), out_segments, info.duration


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _transcribe_openai(wav_path: str, language: str | None) -> tuple[str, list[dict[str, Any]], float]:
    # Use OpenAI transcription API (whisper-1 by default)
    from openai import OpenAI
    from src.services.media import _probe_duration

    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    lang = None if language == "auto" else language
    with open(wav_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model=settings.OPENAI_WHISPER_MODEL,
            file=f,
            language=lang,
            response_format="verbose_json",
        )

    # Try to extract text and segments from the SDK response object
    text = getattr(resp, "text", None)
    segments = getattr(resp, "segments", None)
    if segments is None:
        to_dict = getattr(resp, "to_dict", None)
        model_dump = getattr(resp, "model_dump", None)
        data = None
        if callable(to_dict):
            try:
                data = to_dict()
            except Exception:
                data = None
        if data is None and callable(model_dump):
            try:
                data = model_dump()
            except Exception:
                data = None
        if isinstance(data, dict):
            segments = data.get("segments")
            text = data.get("text", text)

    out_segments: list[dict[str, Any]] = []
    if segments:
        for i, seg in enumerate(segments):
            out_segments.append({
                "id": seg.get("id", i),
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "text": seg.get("text", ""),
            })
        duration = out_segments[-1]["end"] if out_segments else 0.0
    else:
        # Fallback: single segment covering whole file
        duration = _probe_duration(Path(wav_path))
        out_segments = [{"id": 0, "start": 0.0, "end": duration, "text": text or ""}]

    return (text or "").strip(), out_segments, float(duration)


def transcribe(wav_path: str, language: str | None) -> tuple[str, list[dict[str, Any]], float]:
    settings = get_settings()
    if settings.STT_PROVIDER.lower() == "openai":
        return _transcribe_openai(wav_path, language)
    return _transcribe_local(wav_path, language)
