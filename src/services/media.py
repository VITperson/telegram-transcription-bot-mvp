from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import logging
import os
from typing import Iterable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
import datetime as dt
import time


log = logging.getLogger("worker")


class YouTubeDownloadError(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code or ""


def _retry_ytdlp(exc: BaseException) -> bool:
    # Don't retry for explicit YouTube 403s
    return not (isinstance(exc, YouTubeDownloadError) and getattr(exc, "code", "") == "yt_403")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), retry=retry_if_exception(_retry_ytdlp))
def youtube_download_to_wav(url: str) -> tuple[str, float]:
    tmpdir = Path(tempfile.mkdtemp(prefix="yt_"))
    out = tmpdir / "video.%(ext)s"

    # Optional cookies support to bypass YouTube gating if provided
    cookies_path = os.getenv("YTDLP_COOKIES_PATH")
    cookies_args: list[str] = []
    if cookies_path and Path(cookies_path).exists():
        # Try to normalize cookies file to Netscape format if needed
        prepared = _prepare_cookies_file(Path(cookies_path), tmpdir)
        if prepared:
            cookies_args = ["--cookies", prepared]

    # Optional user-agent override
    ua = os.getenv(
        "YTDLP_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    )
    ua_args = ["--user-agent", ua]

    base_args: list[str] = [
        "yt-dlp",
        "--ignore-config",
        "--no-warnings",
        "--no-call-home",
        "--no-playlist",
        "--force-ipv4",
        "--retries",
        "2",
        "--fragment-retries",
        "2",
        # yt-dlp deprecated/removed --timeout; use --socket-timeout
        "--socket-timeout",
        "30",
        "--add-header",
        "Referer: https://www.youtube.com/",
        "-o",
        str(out),
    ] + ua_args + cookies_args

    # Try multiple player clients and formats as fallbacks
    clients: list[str] = [
        "android",
        "web",
        "ios",
        "tv",
    ]
    fmts: list[str] = [
        "bestaudio[ext=m4a]/bestaudio/best",
        "m4a/bestaudio/best",
        "bestaudio",
    ]

    last_err: subprocess.CalledProcessError | None = None
    saw_403 = False
    log.info(f"yt.download.start url={url}")
    for client in clients:
        for fmt in fmts:
            cmd = base_args + [
                "--extractor-args",
                f"youtube:player_client={client}",
                "-f",
                fmt,
                url,
            ]
            try:
                log.info(f"yt.download.try client={client} fmt={fmt}")
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                # success
                dl_files = list(tmpdir.glob("video.*"))
                if not dl_files:
                    log.warning("yt.download.no_file_produced")
                    continue
                source = dl_files[0]
                wav_path, duration = normalize_to_wav(source)
                try:
                    source.unlink(missing_ok=True)
                except Exception:
                    pass
                log.info(f"yt.download.ok client={client} fmt={fmt} duration={duration:.2f}s path={wav_path}")
                return wav_path, duration
            except subprocess.CalledProcessError as e:
                last_err = e
                msg = (e.stderr or "") + "\n" + (e.stdout or "")
                if (
                    "HTTP Error 403" in msg
                    or "403: Forbidden" in msg
                    or "returned HTTP Error 403" in msg
                    or "Sign in to confirm you’re not a bot" in msg
                    or "Sign in to confirm you're not a bot" in msg
                ):
                    saw_403 = True
                    # Try next combination without waiting for Tenacity backoff
                    log.warning(f"yt.download.403 client={client} fmt={fmt}")
                    continue
                # For other yt-dlp failures, try next fmt/client combo before letting
                # Tenacity retry the whole function.
                log.warning(f"yt.download.failed client={client} fmt={fmt} code={e.returncode}")
                continue

    # All attempts failed
    if saw_403:
        raise YouTubeDownloadError(
            "YouTube blocked the download (HTTP 403). Add cookies via YTDLP_COOKIES_PATH to bypass restrictions.",
            code="yt_403",
        )
    if last_err is not None:
        # Provide clearer message to the caller and user
        stderr = (last_err.stderr or "").strip()
        stdout = (last_err.stdout or "").strip()
        snippet = (stderr or stdout or str(last_err))
        if len(snippet) > 400:
            snippet = snippet[:400].rstrip() + "…"
        log.error(f"yt.download.error exit={last_err.returncode} hint={(snippet[:120] + '…') if len(snippet) > 120 else snippet}")
        raise YouTubeDownloadError(
            f"yt-dlp failed (exit {last_err.returncode}). Hint: {snippet}",
            code="yt_dl_failed",
        )
    raise RuntimeError("Download failed: no file produced")


def _parse_expiry_to_epoch(exp: str) -> int:
    exp = exp.strip()
    if not exp or exp.lower() == "session":
        return 0
    # Try integer epoch
    try:
        return int(exp)
    except Exception:
        pass
    # Try ISO 8601
    try:
        # Example: 2026-09-14T18:01:01.250Z
        dt_obj = dt.datetime.fromisoformat(exp.replace("Z", "+00:00"))
        return int(dt_obj.timestamp())
    except Exception:
        return 0


def _prepare_cookies_file(src: Path, tmpdir: Path) -> str | None:
    """Return a path to a Netscape-format cookies file, or None if unusable.

    Accepts Cookie-Editor TSV export (name, value, domain, path, expiry, ...),
    converts to Netscape format when needed.
    """
    try:
        with src.open("r", encoding="utf-8", errors="ignore") as f:
            first = f.readline()
            if first.startswith("# Netscape HTTP Cookie File") or first.startswith("# HTTP Cookie File"):
                return str(src)
            # Not Netscape: attempt to convert TSV lines
            lines = [first] + f.readlines()
    except Exception:
        return None

    out_path = tmpdir / "cookies_netscape.txt"
    try:
        with out_path.open("w", encoding="utf-8") as out:
            out.write("# Netscape HTTP Cookie File\n")
            out.write("# This file was generated by the app to be used by yt-dlp.\n")
            for raw in lines:
                raw = raw.strip()
                if not raw or raw.startswith("#"):
                    continue
                parts = raw.split("\t")
                if len(parts) < 4:
                    continue
                # Heuristic mapping for Cookie-Editor-like TSV:
                # 0:name, 1:value, 2:domain, 3:path, 4:expiry(ISO or epoch) ... 6:httpOnly, 7:secure
                name = parts[0]
                value = parts[1] if len(parts) > 1 else ""
                domain = parts[2] if len(parts) > 2 else ""
                path = parts[3] if len(parts) > 3 else "/"
                expiry = parts[4] if len(parts) > 4 else "0"
                http_only = parts[6] if len(parts) > 6 else ""
                secure = parts[7] if len(parts) > 7 else ""

                include_sub = "TRUE" if domain.startswith(".") else "FALSE"
                secure_flag = "TRUE" if secure in ("1", "true", "TRUE", "✓", "yes", "Yes") else "FALSE"
                # expiry epoch
                expires = _parse_expiry_to_epoch(expiry)
                # Netscape columns: domain, include_subdomains, path, secure, expires, name, value
                out.write(f"{domain}\t{include_sub}\t{path}\t{secure_flag}\t{expires}\t{name}\t{value}\n")
        return str(out_path)
    except Exception:
        return None


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
