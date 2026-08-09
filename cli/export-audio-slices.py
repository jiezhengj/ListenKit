#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SLICE_ID_RE = re.compile(r"S\d{2,}")


def fail(message: str) -> None:
    raise SystemExit(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export audio slices from a JSON time-range manifest.")
    parser.add_argument("--input", required=True, dest="input_path")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--padding-seconds", type=float, default=0.15)
    parser.add_argument("--allow-overlap", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def require_number(value: Any, field: str, slice_id: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"Slice {slice_id} field '{field}' must be a number.")
    return float(value)


def load_manifest(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"Manifest not found: {path}")
    except json.JSONDecodeError as exc:
        fail(f"Manifest JSON is invalid: {path}: {exc}")
    if payload.get("version") != 1:
        fail("Manifest field 'version' must be 1.")
    slices = payload.get("slices")
    if not isinstance(slices, list) or not slices:
        fail("Manifest field 'slices' must be a non-empty list.")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous_end: float | None = None
    for raw in slices:
        if not isinstance(raw, dict):
            fail("Each slice must be an object.")
        slice_id = str(raw.get("id", ""))
        if not SLICE_ID_RE.fullmatch(slice_id):
            fail(f"Slice id must match SNN: {slice_id!r}")
        if slice_id in seen_ids:
            fail(f"Duplicate slice id: {slice_id}")
        start = require_number(raw.get("start"), "start", slice_id)
        end = require_number(raw.get("end"), "end", slice_id)
        if start < 0 or end <= start:
            fail(f"Slice {slice_id} must satisfy 0 <= start < end.")
        if previous_end is not None and start < previous_end:
            fail(f"Slice {slice_id} overlaps the previous slice.")
        seen_ids.add(slice_id)
        normalized.append({"id": slice_id, "start": start, "end": end})
        previous_end = end
    return normalized


def audio_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        fail("ffprobe was not found on PATH.")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        fail(result.stderr.strip() or "ffprobe failed.")
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        fail(f"ffprobe returned an invalid duration: {result.stdout.strip()!r}")
    if duration <= 0:
        fail("Audio duration must be positive.")
    return duration


def padded_ranges(slices: list[dict[str, Any]], duration: float, padding: float, allow_overlap: bool) -> list[dict[str, Any]]:
    if padding < 0:
        fail("--padding-seconds must be non-negative.")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(slices):
        previous = slices[index - 1] if index > 0 else None
        following = slices[index + 1] if index + 1 < len(slices) else None
        start = max(0.0, item["start"] - padding)
        end = min(duration, item["end"] + padding)
        if previous is not None and not allow_overlap:
            start = max(start, (previous["end"] + item["start"]) / 2)
        if following is not None and not allow_overlap:
            end = min(end, (item["end"] + following["start"]) / 2)
        overlap = 0.0
        if result:
            overlap = max(0.0, result[-1]["end"] - start)
        result.append(
            {
                "id": item["id"],
                "start": round(start, 6),
                "end": round(end, 6),
                "overlap_with_previous_seconds": round(overlap, 6),
            }
        )
    return result


def output_path_for(output_dir: Path, input_path: Path, slice_id: str) -> Path:
    return output_dir / f"{input_path.stem}_{slice_id}.m4a"


def export_slices(args: argparse.Namespace) -> dict[str, Any]:
    input_path = Path(args.input_path).expanduser()
    manifest_path = Path(args.manifest).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    if not input_path.is_file():
        fail(f"Input audio file not found: {input_path}")

    slices = load_manifest(manifest_path)
    output_paths = [output_path_for(output_dir, input_path, item["id"]) for item in slices]
    if not args.overwrite:
        for output_path in output_paths:
            if output_path.exists():
                fail(f"Output already exists: {output_path}. Pass --overwrite to replace it.")

    duration = audio_duration(input_path)
    ranges = padded_ranges(slices, duration, args.padding_seconds, args.allow_overlap)
    output_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    report_slices: list[dict[str, Any]] = []
    try:
        for item, output_path in zip(ranges, output_paths):
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                fail("ffmpeg was not found on PATH.")
            result = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    str(item["start"]),
                    "-to",
                    str(item["end"]),
                    "-i",
                    str(input_path),
                    "-vn",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    str(output_path),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                fail(result.stderr.strip() or f"ffmpeg failed for {item['id']}.")
            if not output_path.is_file() or output_path.stat().st_size <= 0:
                fail(f"ffmpeg failed for {item['id']}: output file is missing or empty.")
            exported.append(output_path)
            report_slices.append(
                {
                    "id": item["id"],
                    "start": item["start"],
                    "end": item["end"],
                    "overlap_with_previous_seconds": item["overlap_with_previous_seconds"],
                    "path": str(output_path),
                    "status": "exported",
                }
            )
    except BaseException:
        for output_path in exported:
            output_path.unlink(missing_ok=True)
        raise

    return {"version": 1, "source": str(input_path), "slices": report_slices}


def main() -> int:
    args = parse_args()
    report = export_slices(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
