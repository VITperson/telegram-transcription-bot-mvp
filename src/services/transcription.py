from __future__ import annotations

from typing import Any, List, Dict, Optional
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


def _group_words_into_segments(words: List[Dict[str, Any]], max_len: float) -> List[Dict[str, Any]]:
    """Group word-level timestamps into segments no longer than max_len seconds."""
    segs: List[Dict[str, Any]] = []
    cur_words: List[Dict[str, Any]] = []
    cur_start: Optional[float] = None
    for w in words:
        ws = float(w.get("start", 0.0) or 0.0)
        we = float(w.get("end", ws) or ws)
        if cur_start is None:
            cur_start = ws
        # if adding this word exceeds max_len, flush current segment
        if cur_start is not None and we - cur_start > max_len and cur_words:
            text = " ".join(str(x.get("word", "")).strip() for x in cur_words if str(x.get("word", "")).strip())
            segs.append({"id": len(segs), "start": cur_start, "end": float(cur_words[-1].get("end", cur_start)), "text": text})
            cur_words = []
            cur_start = ws
        cur_words.append({"word": w.get("word", ""), "start": ws, "end": we})
    if cur_words:
        text = " ".join(str(x.get("word", "")).strip() for x in cur_words if str(x.get("word", "")).strip())
        segs.append({"id": len(segs), "start": float(cur_words[0].get("start", 0.0)), "end": float(cur_words[-1].get("end", 0.0)), "text": text})
    return segs


def _split_text_evenly(text: str, duration: float, max_len: float) -> List[Dict[str, Any]]:
    """Fallback splitter with no timestamps: split text across duration into ~max_len chunks.

    Tries to cut at whitespace/punctuation closest to ideal positions.
    """
    if duration <= 0 or not text.strip():
        return [{"id": 0, "start": 0.0, "end": max(0.0, duration), "text": text.strip()}]
    import math

    n = max(1, math.ceil(duration / max_len))
    total_chars = max(1, len(text))
    cuts: List[int] = [0]
    for i in range(1, n):
        ideal = int(i * total_chars / n)
        # search +/- 30 chars for a good split
        lo = max(0, ideal - 30)
        hi = min(total_chars - 1, ideal + 30)
        best = None
        for idx in range(ideal, hi):
            if text[idx] in ".!?\n " and idx > 0:
                best = idx
                break
        if best is None:
            for idx in range(ideal, lo, -1):
                if text[idx] in ".!?\n " and idx > 0:
                    best = idx
                    break
        cuts.append(best if best is not None else ideal)
    cuts.append(total_chars)

    segs: List[Dict[str, Any]] = []
    for i in range(len(cuts) - 1):
        ch_start, ch_end = cuts[i], cuts[i + 1]
        seg_text = text[ch_start:ch_end].strip()
        seg_start = (duration * ch_start) / total_chars
        seg_end = (duration * ch_end) / total_chars
        segs.append({"id": i, "start": seg_start, "end": seg_end, "text": seg_text})
    return segs


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _transcribe_local(wav_path: str, language: str | None) -> tuple[str, list[dict[str, Any]], float]:
    model = _get_local_model()
    segments, info = model.transcribe(
        wav_path,
        language=None if language == "auto" else language,
        word_timestamps=True,  # richer timestamps for post-splitting
    )
    # Build word list for post-split
    words: List[Dict[str, Any]] = []
    out_segments: list[dict[str, Any]] = []
    texts = []
    for seg in segments:
        # collect words if available
        if getattr(seg, "words", None):
            for w in seg.words:
                words.append({
                    "word": getattr(w, "word", ""),
                    "start": float(getattr(w, "start", 0.0) or 0.0),
                    "end": float(getattr(w, "end", 0.0) or 0.0),
                })
        out_segments.append({
            "id": seg.id,
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        })
        texts.append(seg.text)
    text = " ".join(texts).strip()
    # Enforce max segment length if configured
    settings = get_settings()
    max_len = float(getattr(settings, "MAX_SEGMENT_SECONDS", 0) or 0)
    if max_len > 0:
        if words:
            out_segments = _group_words_into_segments(words, max_len)
        else:
            # naive split by duration using existing segments
            duration = float(info.duration or 0.0)
            out_segments = _split_text_evenly(text, duration, max_len)
    return text, out_segments, float(info.duration or 0.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _transcribe_openai(wav_path: str, language: str | None) -> tuple[str, list[dict[str, Any]], float]:
    """Transcribe via OpenAI API and enforce short segments using word timestamps when possible."""
    from openai import OpenAI
    from src.services.media import _probe_duration

    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    lang = None if language == "auto" else language

    model_name = settings.OPENAI_WHISPER_MODEL
    req: dict[str, Any] = {"model": model_name, "language": lang}
    # Ask for rich timestamps
    if model_name.startswith("whisper"):
        req["response_format"] = "verbose_json"
    else:
        req["response_format"] = "json"
        if "transcribe" in model_name or model_name.startswith("gpt-"):
            req["timestamp_granularities"] = ["segment", "word"]

    # Optional: lower temperature for determinism (drop if unsupported)
    transcribe_temp = getattr(settings, "OPENAI_TRANSCRIBE_TEMPERATURE", None)
    if transcribe_temp is not None:
        try:
            req["temperature"] = float(transcribe_temp)
        except Exception:
            pass

    with open(wav_path, "rb") as f:
        req["file"] = f
        try:
            resp = client.audio.transcriptions.create(**req)  # type: ignore[arg-type]
        except Exception as e:
            msg = str(e)
            if "timestamp_granularities" in req and (
                "timestamp_granularities" in msg or "Unrecognized request argument" in msg or "unsupported" in msg
            ):
                req.pop("timestamp_granularities", None)
                resp = client.audio.transcriptions.create(**req)  # type: ignore[arg-type]
            elif "temperature" in req and ("temperature" in msg or "Unsupported value" in msg or "does not support" in msg):
                req.pop("temperature", None)
                resp = client.audio.transcriptions.create(**req)  # type: ignore[arg-type]
            else:
                raise

    # Extract fields from SDK object or its dict form
    text = getattr(resp, "text", None)
    segments = getattr(resp, "segments", None)
    words_attr = getattr(resp, "words", None)
    if segments is None or words_attr is None:
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
            segments = data.get("segments", segments)
            words_attr = data.get("words", words_attr)
            text = data.get("text", text)

    out_segments: list[dict[str, Any]] = []
    # Build initial segments and duration
    if segments:
        for i, seg in enumerate(segments):
            if isinstance(seg, dict):
                sid = seg.get("id", i)
                start = float(seg.get("start", 0.0) or 0.0)
                end = float(seg.get("end", 0.0) or 0.0)
                text_seg = seg.get("text", "") or ""
            else:
                sid = getattr(seg, "id", i)
                start = float(getattr(seg, "start", 0.0) or 0.0)
                end = float(getattr(seg, "end", 0.0) or 0.0)
                text_seg = getattr(seg, "text", "") or ""
            out_segments.append({"id": sid, "start": start, "end": end, "text": text_seg})
        duration = float(out_segments[-1]["end"]) if out_segments else 0.0
    else:
        duration = _probe_duration(Path(wav_path))
        out_segments = [{"id": 0, "start": 0.0, "end": float(duration), "text": text or ""}]

    # Parse words list for fine-grained split
    words_list: List[Dict[str, Any]] = []
    if words_attr and isinstance(words_attr, list):
        for w in words_attr:
            if isinstance(w, dict):
                words_list.append({
                    "word": w.get("word", ""),
                    "start": float(w.get("start", 0.0) or 0.0),
                    "end": float(w.get("end", 0.0) or 0.0),
                })
            else:
                words_list.append({
                    "word": getattr(w, "word", ""),
                    "start": float(getattr(w, "start", 0.0) or 0.0),
                    "end": float(getattr(w, "end", 0.0) or 0.0),
                })

    # Enforce max segment length
    settings = get_settings()
    max_len = float(getattr(settings, "MAX_SEGMENT_SECONDS", 0) or 0)
    if max_len > 0:
        if words_list:
            out_segments = _group_words_into_segments(words_list, max_len)
        else:
            out_segments = _split_text_evenly(text or "", float(duration), max_len)

    return (text or "").strip(), out_segments, float(duration)


def transcribe(wav_path: str, language: str | None) -> tuple[str, list[dict[str, Any]], float]:
    settings = get_settings()
    if settings.STT_PROVIDER.lower() == "openai":
        return _transcribe_openai(wav_path, language)
    return _transcribe_local(wav_path, language)

