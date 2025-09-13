from __future__ import annotations

from typing import Any
from faster_whisper import WhisperModel
from tenacity import retry, stop_after_attempt, wait_exponential
from src.core.config import get_settings


_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        settings = get_settings()
        _model = WhisperModel(settings.WHISPER_MODEL_SIZE, compute_type=settings.WHISPER_COMPUTE_TYPE)
    return _model


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def transcribe(wav_path: str, language: str | None) -> tuple[str, list[dict[str, Any]], float]:
    model = get_model()
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

