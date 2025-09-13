from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def youtube_download_to_wav(url: str) -> tuple[str, float]:
    tmpdir = Path(tempfile.mkdtemp(prefix="yt_"))
    out = tmpdir / "video.%(ext)s"
    cmd = [
        "yt-dlp",
        "-f",
        "bestaudio[ext=m4a]/bestaudio/best",
        "-o",
        str(out),
        url,
    ]
    subprocess.run(cmd, check=True)
    # Find downloaded file
    dl_files = list(tmpdir.glob("video.*"))
    if not dl_files:
        raise RuntimeError("Download failed")
    source = dl_files[0]
    wav_path, duration = normalize_to_wav(source)
    try:
        source.unlink(missing_ok=True)
    except Exception:
        pass
    return wav_path, duration


def _probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def normalize_to_wav(source_path: str | Path) -> tuple[str, float]:
    source = Path(source_path)
    tmpdir = Path(tempfile.mkdtemp(prefix="norm_"))
    wav_path = tmpdir / "audio.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "wav",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True)
    duration = _probe_duration(wav_path)
    return str(wav_path), duration


def cleanup_temp_file(path: str) -> None:
    try:
        p = Path(path)
        d = p.parent
        if p.exists():
            p.unlink()
        # remove parent tmpdir if empty
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    except Exception:
        pass

