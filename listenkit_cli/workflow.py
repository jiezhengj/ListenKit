from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping

from .errors import ListenKitError
from .media import import_audio
from .process import find_command, run_command
from .rendering import render_transcript
from .subtitles import extract_subtitles
from .transcription import transcribe_audio

LANGUAGE_LOCALES = {
    "Japanese": "ja-JP",
    "japanese": "ja-JP",
    "日本語": "ja-JP",
    "日语": "ja-JP",
    "日語": "ja-JP",
    "ja": "ja-JP",
    "ja-JP": "ja-JP",
    "English": "en-US",
    "english": "en-US",
    "英語": "en-US",
    "英语": "en-US",
    "en": "en-US",
    "en-US": "en-US",
    "Chinese": "zh-CN",
    "chinese": "zh-CN",
    "中文": "zh-CN",
    "汉语": "zh-CN",
    "漢語": "zh-CN",
    "zh": "zh-CN",
    "zh-CN": "zh-CN",
    "Korean": "ko-KR",
    "korean": "ko-KR",
    "한국어": "ko-KR",
    "韓語": "ko-KR",
    "韩语": "ko-KR",
    "ko": "ko-KR",
    "ko-KR": "ko-KR",
}


def locale_from_language(language: str) -> str:
    try:
        return LANGUAGE_LOCALES[language]
    except KeyError as exc:
        raise ListenKitError(
            f"Cannot derive ASR locale from --language: {language}. Pass --locale explicitly."
        ) from exc


def title_from_url(url: str) -> str | None:
    yt_dlp = find_command("yt-dlp")
    if not yt_dlp:
        return None
    result = run_command(
        [
            yt_dlp,
            "--quiet",
            "--no-warnings",
            "--skip-download",
            "--no-playlist",
            "--print",
            "title",
            url,
        ],
        check=False,
    )
    if result.returncode != 0:
        return None
    return next((line.strip() for line in result.stdout.splitlines() if line.strip()), None)


def generate_markdown(
    *,
    output: Path,
    language: str,
    url: str | None = None,
    input_path: Path | None = None,
    title: str | None = None,
    locale: str | None = None,
    engine: str = "auto",
    device: str | None = None,
    compute_type: str | None = None,
    device_index: int | None = None,
    auto_init: bool = False,
    audio_format: str = "m4a",
    audio_quality: str = "0",
    filename_template: str | None = None,
    write_info_json: bool = False,
    write_thumbnail: bool = False,
    environment: Mapping[str, str] | None = None,
) -> Path:
    if bool(url) == bool(input_path):
        raise ListenKitError("Exactly one of --url or --input is required.")
    env = dict(os.environ if environment is None else environment)
    if input_path is not None and (
        audio_quality != "0"
        or filename_template is not None
        or write_info_json
        or write_thumbnail
    ):
        raise ListenKitError(
            "--quality, --filename-template, --write-info-json, and --write-thumbnail "
            "are only valid with --url."
        )
    selected_locale = locale or locale_from_language(language)
    output = output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    transcript_json = output.with_suffix(".json")
    output_stem = output.stem
    source_ref = url or str(input_path)
    selected_title = title
    url_title = title_from_url(url) if url and not title else None
    subtitle_available = False

    if url:
        try:
            extract_subtitles(url, locale=selected_locale, output=transcript_json)
            subtitle_available = True
        except ListenKitError:
            pass

    try:
        audio_paths = import_audio(
            output_dir=output.parent / "audio",
            url=url,
            input_path=input_path,
            base_name=output_stem,
            audio_format=audio_format,
            audio_quality=audio_quality,
            filename_template=filename_template,
            write_info_json=write_info_json,
            write_thumbnail=write_thumbnail,
        )
    except ListenKitError as exc:
        if url and subtitle_available:
            print(
                "Audio import failed after subtitles were extracted. Markdown will be "
                "generated from subtitles, but no local listening audio was created.\n"
                f"Audio import error: {exc}",
                file=sys.stderr,
            )
            selected_title = selected_title or url_title or output_stem
            render_transcript(
                source_ref=source_ref,
                transcript_json=transcript_json,
                title=selected_title,
                language=language,
                output=output,
            )
            return output
        raise exc

    if len(audio_paths) != 1:
        raise ListenKitError("Import produced multiple audio paths; expected a single input.")
    audio_path = audio_paths[0]
    selected_title = selected_title or url_title
    if not selected_title:
        selected_title = input_path.stem if input_path else audio_path.stem
    if not subtitle_available:
        transcribe_audio(
            audio_path=audio_path,
            locale=selected_locale,
            engine=engine,
            output=transcript_json,
            auto_init=auto_init,
            device=device,
            compute_type=compute_type,
            device_index=device_index,
            environment=env,
        )
    render_transcript(
        source_ref=source_ref,
        transcript_json=transcript_json,
        title=selected_title,
        language=language,
        output=output,
    )
    return output
