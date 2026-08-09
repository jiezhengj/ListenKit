from __future__ import annotations

import html
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .errors import CommandExecutionError, ListenKitError
from .process import require_command, run_command

TIMING_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+"
    r"(?P<end>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")


def parse_timestamp(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        hours = "0"
        minutes, seconds = parts
    else:
        hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def clean_subtitle_text(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_vtt(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    segments: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        timing = TIMING_RE.search(lines[index].strip())
        if not timing:
            index += 1
            continue
        start = parse_timestamp(timing.group("start"))
        end = parse_timestamp(timing.group("end"))
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index])
            index += 1
        text = clean_subtitle_text(text_lines)
        if text:
            segments.append({"start": start, "end": end, "text": text})
        index += 1
    return segments


def write_transcript_json(
    vtt_path: Path,
    *,
    locale: str,
    subtitle_kind: str,
    output: Path,
) -> Path:
    segments = parse_vtt(vtt_path)
    if not segments:
        raise ListenKitError(f"No usable subtitle cues found in: {vtt_path}")
    payload = {
        "schema_version": 1,
        "engine": "yt-dlp-subtitles",
        "locale": locale,
        "subtitle_kind": subtitle_kind,
        "full_text": "\n".join(str(segment["text"]) for segment in segments),
        "segments": segments,
        "timing_complete": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(output, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return output


def extract_subtitles(url: str, *, locale: str, output: Path) -> Path:
    yt_dlp = require_command("yt-dlp")
    language = locale.split("-", 1)[0].lower()
    with tempfile.TemporaryDirectory(prefix="listenkit-subtitles-") as raw_work_dir:
        work_dir = Path(raw_work_dir)
        for kind, flag in (("manual", "--write-subs"), ("auto", "--write-auto-subs")):
            _clear_vtt_files(work_dir)
            result = run_command(
                [
                    yt_dlp,
                    "--quiet",
                    "--no-warnings",
                    "--skip-download",
                    flag,
                    "--sub-langs",
                    language,
                    "--sub-format",
                    "vtt",
                    "--paths",
                    work_dir,
                    "--output",
                    "subtitle.%(ext)s",
                    url,
                ],
                check=False,
            )
            if result.returncode != 0:
                continue
            candidates = sorted(
                work_dir.rglob("*.vtt"),
                key=lambda value: value.as_posix().casefold(),
            )
            for candidate in candidates:
                try:
                    return write_transcript_json(
                        candidate,
                        locale=locale,
                        subtitle_kind=kind,
                        output=output,
                    )
                except ListenKitError:
                    continue
    raise ListenKitError(f"No usable subtitles found for URL and locale: {url} ({locale})")


def _clear_vtt_files(root: Path) -> None:
    for path in root.rglob("*.vtt"):
        if path.is_file():
            path.unlink()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        import os

        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
