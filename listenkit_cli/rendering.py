from __future__ import annotations

import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ListenKitError

CURRENT_TRANSCRIPT_SCHEMA_VERSION = 1


def load_transcript(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ListenKitError(f"Invalid transcript JSON: {path}: {exc}") from exc
    if payload.get("error"):
        error = payload["error"]
        if isinstance(error, dict):
            raise ListenKitError(
                "Transcript JSON contains ASR error: "
                f"{error.get('type', 'error')}: {error.get('message', 'transcription failed')}"
            )
        raise ListenKitError(f"Transcript JSON contains ASR error: {error}")
    schema_version = payload.get("schema_version")
    if schema_version is not None and schema_version != CURRENT_TRANSCRIPT_SCHEMA_VERSION:
        raise ListenKitError(f"Unsupported transcript schema_version: {schema_version}")
    required = ["engine", "locale", "full_text", "segments", "timing_complete"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ListenKitError(
            f"Transcript JSON is missing required keys: {', '.join(missing)}"
        )
    if not isinstance(payload["segments"], list):
        raise ListenKitError("Transcript JSON field 'segments' must be a list.")
    return payload


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def transcript_text(payload: dict[str, Any]) -> str:
    full_text = clean_text(str(payload.get("full_text", "")))
    if full_text:
        return full_text
    parts: list[str] = []
    for segment in payload.get("segments", []):
        if isinstance(segment, dict):
            value = clean_text(str(segment.get("text", "")))
            if value:
                parts.append(value)
    return "\n".join(parts).strip() or "_No transcript text was generated._"


def render_markdown(
    *, source_ref: str, title: str, language: str, payload: dict[str, Any]
) -> str:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", source_ref):
        source = f"- Source: <{source_ref}>"
    else:
        source = f"- Source: `{source_ref}`"
    timing = "yes" if payload.get("timing_complete") else "partial or unavailable"
    runtime_lines = []
    if payload.get("device"):
        runtime_lines.append(f"- ASR device: `{payload['device']}`")
    if payload.get("compute_type"):
        runtime_lines.append(f"- Compute type: `{payload['compute_type']}`")
    if payload.get("fallback_reason"):
        fallback_reason = clean_text(str(payload["fallback_reason"])).replace("\n", " ")
        runtime_lines.append(f"- Acceleration fallback: {fallback_reason}")
    return "\n".join(
        [
            f"# {title}",
            "",
            "## Source",
            "",
            source,
            f"- Language: {language}",
            f"- Locale: `{payload.get('locale')}`",
            f"- Transcript engine: `{payload.get('engine')}`",
            *runtime_lines,
            f"- Timing complete: {timing}",
            f"- Generated at: {generated_at}",
            "",
            "## Transcript",
            "",
            transcript_text(payload),
            "",
        ]
    )


def render_transcript(
    *,
    source_ref: str,
    transcript_json: Path,
    title: str,
    language: str,
    output: Path,
) -> Path:
    payload = load_transcript(transcript_json)
    content = render_markdown(
        source_ref=source_ref, title=title, language=language, payload=payload
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        import os

        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output
