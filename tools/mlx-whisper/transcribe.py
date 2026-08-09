#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe one audio file with MLX Whisper.")
    parser.add_argument("audio_path")
    parser.add_argument("--locale", default="ja-JP")
    parser.add_argument("--model", default="mlx-community/whisper-small-mlx")
    return parser.parse_args()


def emit(payload: dict, status: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return status


def locale_to_language(locale: str) -> str | None:
    return locale.split("-", 1)[0].lower() if locale else None


def main() -> int:
    args = parse_args()
    audio_path = Path(args.audio_path)
    if not audio_path.is_file():
        return emit(
            {
                "schema_version": 1,
                "error": {
                    "type": "file_not_found",
                    "message": f"Audio file not found: {audio_path}",
                },
            },
            1,
        )
    try:
        import mlx.core as mx
        import mlx_whisper

        if not mx.metal.is_available():
            raise RuntimeError("MLX is installed, but no Metal device is available")
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=args.model,
            language=locale_to_language(args.locale),
            verbose=None,
            condition_on_previous_text=False,
            word_timestamps=False,
        )
        segments = [
            {
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "text": str(segment.get("text", "")).strip(),
            }
            for segment in result.get("segments", [])
            if str(segment.get("text", "")).strip()
        ]
        full_text = str(result.get("text", "")).strip()
        if not full_text:
            full_text = "\n".join(segment["text"] for segment in segments)
        return emit(
            {
                "schema_version": 1,
                "engine": "mlx-whisper",
                "model": args.model,
                "device": "metal",
                "device_index": 0,
                "compute_type": "float16",
                "locale": args.locale,
                "language": result.get("language") or locale_to_language(args.locale),
                "language_probability": result.get("language_probability"),
                "full_text": full_text,
                "segments": segments,
                "timing_complete": all(
                    segment["end"] >= segment["start"] for segment in segments
                ),
            }
        )
    except Exception as exc:
        print(f"mlx-whisper failed: {exc}", file=sys.stderr)
        return emit(
            {
                "schema_version": 1,
                "error": {"type": exc.__class__.__name__, "message": str(exc)},
            },
            1,
        )


if __name__ == "__main__":
    raise SystemExit(main())
