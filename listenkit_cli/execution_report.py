from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import __version__
from .errors import ListenKitError

EXECUTION_REPORT_SCHEMA_VERSION = 1

_TRANSCRIPTION_METADATA_KEYS = (
    "schema_version",
    "engine",
    "model",
    "device",
    "device_index",
    "device_name",
    "compute_type",
    "device_selection_reason",
    "fallback_from",
    "fallback_reason",
    "locale",
    "language",
    "timing_complete",
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def transcription_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in _TRANSCRIPTION_METADATA_KEYS if key in payload}


def read_transcription_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ListenKitError(
            f"Unable to read transcript metadata for execution report: {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ListenKitError(
            f"Transcript payload must be a JSON object for execution report: {path}"
        )
    return payload


def parse_transcription_payload(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ListenKitError(
            f"Unable to parse transcript metadata for execution report: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ListenKitError("Transcript payload must be a JSON object for execution report.")
    return payload


def write_execution_report(
    path: Path,
    *,
    command: str,
    status: str,
    started_at: str,
    finished_at: str,
    duration_seconds: float,
    outputs: Mapping[str, str] | None = None,
    transcription: Mapping[str, Any] | None = None,
    error: BaseException | None = None,
) -> Path:
    payload: dict[str, Any] = {
        "schema_version": EXECUTION_REPORT_SCHEMA_VERSION,
        "listenkit_version": __version__,
        "command": command,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": round(max(duration_seconds, 0.0), 6),
        "outputs": dict(outputs or {}),
    }
    if transcription is not None:
        payload["transcription"] = transcription_metadata(transcription)
    if error is not None:
        payload["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }

    destination = path.expanduser()
    temporary: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(temporary_name)
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary.replace(destination)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise ListenKitError(
            f"Unable to write execution report: {destination}: {exc}"
        ) from exc
    return destination
