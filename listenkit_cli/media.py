from __future__ import annotations

import os
import re
from pathlib import Path

from .errors import ListenKitError
from .process import require_command, run_command

SUPPORTED_AUDIO_FORMATS = {"mp3", "m4a", "wav", "flac"}
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def validate_base_name(value: str) -> None:
    if not value or value in {".", ".."}:
        raise ListenKitError("--base-name must be a non-empty filename stem.")
    if "/" in value or "\\" in value or "\x00" in value:
        raise ListenKitError("--base-name must not contain path separators.")
    portable_stem = value.rstrip(" .").split(".", 1)[0].upper()
    if portable_stem in WINDOWS_RESERVED_NAMES:
        raise ListenKitError(f"--base-name is reserved on Windows: {value}")
    if any(character in value for character in '<>:"|?*'):
        raise ListenKitError(f"--base-name contains a character unsupported on Windows: {value}")


def paths_refer_to_same_file(first: Path, second: Path) -> bool:
    try:
        return first.samefile(second)
    except (FileNotFoundError, OSError):
        left = os.path.normcase(os.path.abspath(first))
        right = os.path.normcase(os.path.abspath(second))
        return left == right


def import_audio(
    *,
    output_dir: Path,
    url: str | None = None,
    input_path: Path | None = None,
    base_name: str | None = None,
    audio_format: str = "m4a",
    audio_quality: str = "0",
    filename_template: str | None = None,
    write_info_json: bool = False,
    write_thumbnail: bool = False,
    playlist: bool = False,
) -> list[Path]:
    if bool(url) == bool(input_path):
        raise ListenKitError("Exactly one of --url or --input is required.")
    if audio_format not in SUPPORTED_AUDIO_FORMATS:
        raise ListenKitError("--format must be one of: mp3, m4a, wav, flac")
    if base_name is not None:
        validate_base_name(base_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path is not None:
        source = input_path.expanduser()
        if not source.is_file():
            raise ListenKitError(f"Input audio file not found: {source}")
        stem = base_name or source.stem
        validate_base_name(stem)
        output = output_dir / f"{stem}.{audio_format}"
        if paths_refer_to_same_file(source, output):
            return [output]
        ffmpeg = require_command("ffmpeg")
        result = run_command(
            [ffmpeg, "-y", "-i", source, "-vn", output],
            check=False,
        )
        if result.returncode != 0:
            output.unlink(missing_ok=True)
            error = (result.stderr or "").strip()
            raise ListenKitError(error or f"ffmpeg failed with exit {result.returncode}")
        if not output.is_file():
            raise ListenKitError(f"ffmpeg did not create expected output: {output}")
        return [output]

    yt_dlp = require_command("yt-dlp")
    require_command("ffmpeg")
    template = filename_template or "%(title)s.%(ext)s"
    if base_name and not filename_template:
        template = f"{base_name}.%(ext)s"
    command: list[str | os.PathLike[str]] = [
        yt_dlp,
        "--quiet",
        "--no-warnings",
        "--extract-audio",
        "--audio-format",
        audio_format,
        "--audio-quality",
        audio_quality,
        "--add-metadata",
        "--embed-metadata",
        "--no-mtime",
        "--print",
        "after_move:filepath",
        "--paths",
        output_dir,
        "--output",
        template,
        "--yes-playlist" if playlist else "--no-playlist",
    ]
    if write_info_json:
        command.append("--write-info-json")
    if write_thumbnail:
        command.append("--write-thumbnail")
    command.append(url or "")
    result = run_command(command, check=False)
    if result.returncode != 0:
        error = (result.stderr or "").strip()
        raise ListenKitError(error or f"yt-dlp failed with exit {result.returncode}")
    paths = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    if not paths:
        raise ListenKitError("yt-dlp did not report an imported audio path.")
    if not playlist and len(paths) != 1:
        raise ListenKitError("yt-dlp produced multiple paths in single-item mode.")
    return paths
