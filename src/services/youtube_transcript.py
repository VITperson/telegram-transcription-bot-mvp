from __future__ import annotations

from typing import Iterable, Tuple, List, Dict
from urllib.parse import urlparse, parse_qs
import re

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript


_YT_REGEXPS = [
    re.compile(r"https?://(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_\-]{11})"),
    re.compile(r"https?://(?:www\.)?youtu\.be/([A-Za-z0-9_\-]{11})"),
    re.compile(r"https?://(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_\-]{11})"),
]


def _extract_video_id(url: str) -> str:
    for rx in _YT_REGEXPS:
        m = rx.match(url)
        if m:
            return m.group(1)
    # fallback parse
    p = urlparse(url)
    qs = parse_qs(p.query)
    if "v" in qs and qs["v"]:
        cand = qs["v"][0]
        if re.fullmatch(r"[A-Za-z0-9_\-]{11}", cand):
            return cand
    raise ValueError("Cannot extract YouTube video id from URL")


def fetch_youtube_transcript(url: str, preferred_langs: Iterable[str] | None = None) -> Tuple[str, List[Dict], float]:
    """Fetch YouTube transcript if available and return (text, segments, duration).

    preferred_langs: iterable of language codes in order of preference.
    The function tries manually created transcript first, then auto-generated.
    """
    vid = _extract_video_id(url)
    langs = [l.strip() for l in (preferred_langs or []) if l and l.strip()]
    try:
        listing = YouTubeTranscriptApi.list_transcripts(vid)
    except TranscriptsDisabled as e:
        raise RuntimeError("Transcripts are disabled for this video") from e
    except CouldNotRetrieveTranscript as e:
        raise RuntimeError("Could not retrieve transcripts (rate-limited or blocked)") from e
    except Exception as e:
        raise

    transcript = None
    # Try exact language manual transcript
    for lang in langs:
        try:
            transcript = listing.find_transcript([lang])
            break
        except Exception:
            continue
    # Try generated transcript
    if transcript is None:
        for lang in langs:
            try:
                transcript = listing.find_manually_created_transcript([lang])
                break
            except Exception:
                continue
    if transcript is None:
        # any English
        try:
            transcript = listing.find_transcript(["en", "en-US", "en-GB"])  # type: ignore[arg-type]
        except Exception:
            try:
                transcript = listing.find_generated_transcript(["en", "en-US", "en-GB"])  # type: ignore[arg-type]
            except Exception as e:
                # As a last resort, take the first available
                try:
                    transcript = next(iter(listing))
                except Exception:
                    raise RuntimeError("No transcript found for this video") from e

    entries = transcript.fetch()
    segments: List[Dict] = []
    texts: List[str] = []
    last_end = 0.0
    for i, it in enumerate(entries):
        start = float(it.get("start", 0.0))
        dur = float(it.get("duration", 0.0))
        end = start + dur
        text = it.get("text", "")
        segments.append({"id": i, "start": start, "end": end, "text": text})
        texts.append(text)
        last_end = max(last_end, end)
    return " ".join(t.strip() for t in texts).strip(), segments, last_end

