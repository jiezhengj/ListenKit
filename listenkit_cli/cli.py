from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Sequence

from .asr_device import ALLOWED_COMPUTE_TYPES
from .agent_install import install_instructions, instruction_source
from .doctor import doctor_lines
from .errors import ListenKitError
from .execution_report import (
    parse_transcription_payload,
    read_transcription_payload,
    utc_timestamp,
    write_execution_report,
)
from .health import inspect_runtime
from .media import import_audio
from .platform_paths import default_runtime_dir, selected_runtime_python
from .rendering import render_transcript
from .runtime import initialize_runtime
from .subtitles import extract_subtitles
from .transcription import transcribe_audio
from .workflow import generate_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="listenkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate-markdown",
        help="Generate transcript Markdown and same-stem JSON from one URL or local media file.",
    )
    source = generate.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--input", type=Path)
    generate.add_argument("--language", required=True)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--title")
    generate.add_argument("--locale")
    generate.add_argument(
        "--engine",
        default="auto",
        choices=["auto", "faster-whisper", "mlx", "apple"],
    )
    generate.add_argument("--device", choices=["auto", "cpu", "cuda"])
    generate.add_argument("--compute-type", choices=sorted(ALLOWED_COMPUTE_TYPES))
    generate.add_argument("--device-index", type=int)
    generate.add_argument("--auto-init", action="store_true")
    generate.add_argument("--format", default="m4a", choices=["mp3", "m4a", "wav", "flac"])
    generate.add_argument("--quality", default="0")
    generate.add_argument("--filename-template")
    generate.add_argument("--write-info-json", action="store_true")
    generate.add_argument("--write-thumbnail", action="store_true")
    generate.add_argument(
        "--report-json",
        type=Path,
        help="Write an atomic machine-readable execution report.",
    )

    importer = subparsers.add_parser("import-audio", help="Import one URL or local media file.")
    import_source = importer.add_mutually_exclusive_group(required=True)
    import_source.add_argument("--url")
    import_source.add_argument("--input", type=Path)
    importer.add_argument("--output-dir", type=Path, required=True)
    importer.add_argument("--base-name")
    importer.add_argument("--format", default="m4a", choices=["mp3", "m4a", "wav", "flac"])
    importer.add_argument("--quality", default="0")
    importer.add_argument("--filename-template")
    importer.add_argument("--write-info-json", action="store_true")
    importer.add_argument("--write-thumbnail", action="store_true")
    importer.add_argument("--playlist", action="store_true")

    subtitles = subparsers.add_parser("extract-subtitles", help="Extract URL subtitles as transcript JSON.")
    subtitles.add_argument("--url", required=True)
    subtitles.add_argument("--locale", required=True)
    subtitles.add_argument("--output", type=Path, required=True)

    transcribe = subparsers.add_parser("transcribe-audio", help="Transcribe one local audio file.")
    transcribe.add_argument("--audio-path", type=Path, required=True)
    transcribe.add_argument("--locale", required=True)
    transcribe.add_argument(
        "--engine",
        default="auto",
        choices=["auto", "faster-whisper", "mlx", "apple"],
    )
    transcribe.add_argument("--device", choices=["auto", "cpu", "cuda"])
    transcribe.add_argument("--compute-type", choices=sorted(ALLOWED_COMPUTE_TYPES))
    transcribe.add_argument("--device-index", type=int)
    transcribe.add_argument("--output", type=Path)
    transcribe.add_argument("--auto-init", action="store_true")
    transcribe.add_argument(
        "--report-json",
        type=Path,
        help="Write an atomic machine-readable execution report.",
    )

    render = subparsers.add_parser("render", help="Render transcript JSON as Markdown.")
    render.add_argument("--source-ref", required=True)
    render.add_argument("--transcript-json", type=Path, required=True)
    render.add_argument("--title", required=True)
    render.add_argument("--language", required=True)
    render.add_argument("--output", type=Path, required=True)

    init_runtime = subparsers.add_parser(
        "init-runtime", help="Create or repair the managed local ASR runtime."
    )
    init_runtime.add_argument("--runtime-dir", type=Path)
    init_runtime.add_argument("--force-repair", action="store_true")
    init_runtime.add_argument("--print-runtime-dir", action="store_true")

    check_runtime = subparsers.add_parser("check-runtime", help="Validate the faster-whisper runtime without modifying it.")
    check_runtime.add_argument("--python", type=Path)

    install = subparsers.add_parser("install-agent-instructions", help="Install generic agent instructions.")
    install.add_argument("--target", type=Path)
    install.add_argument("--force", action="store_true")
    install.add_argument("--dry-run", action="store_true")
    install.add_argument("--print", dest="print_only", action="store_true")

    subparsers.add_parser("doctor", help="Report platform, dependency, and runtime status.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    started_at = utc_timestamp()
    started_monotonic = time.monotonic()
    try:
        _validate_report_destination(args)
        return _dispatch(
            args,
            parser,
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
    except ListenKitError as exc:
        _write_error_report(args, exc, started_at, started_monotonic)
        print(str(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        _write_error_report(args, exc, started_at, started_monotonic)
        print(str(exc), file=sys.stderr)
        return 1


def _dispatch(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    *,
    started_at: str,
    started_monotonic: float,
) -> int:
    if args.command == "generate-markdown":
        output = generate_markdown(
            output=args.output,
            language=args.language,
            url=args.url,
            input_path=args.input,
            title=args.title,
            locale=args.locale,
            engine=args.engine,
            device=args.device,
            compute_type=args.compute_type,
            device_index=args.device_index,
            auto_init=args.auto_init,
            audio_format=args.format,
            audio_quality=args.quality,
            filename_template=args.filename_template,
            write_info_json=args.write_info_json,
            write_thumbnail=args.write_thumbnail,
        )
        if args.report_json:
            transcript_path = output.with_suffix(".json")
            write_execution_report(
                args.report_json,
                command=args.command,
                status="ok",
                started_at=started_at,
                finished_at=utc_timestamp(),
                duration_seconds=time.monotonic() - started_monotonic,
                outputs={
                    "markdown": str(output),
                    "transcript_json": str(transcript_path),
                },
                transcription=read_transcription_payload(transcript_path),
            )
        print(output)
        return 0
    if args.command == "import-audio":
        paths = import_audio(
            output_dir=args.output_dir,
            url=args.url,
            input_path=args.input,
            base_name=args.base_name,
            audio_format=args.format,
            audio_quality=args.quality,
            filename_template=args.filename_template,
            write_info_json=args.write_info_json,
            write_thumbnail=args.write_thumbnail,
            playlist=args.playlist,
        )
        for path in paths:
            print(path)
        return 0
    if args.command == "extract-subtitles":
        print(extract_subtitles(args.url, locale=args.locale, output=args.output))
        return 0
    if args.command == "transcribe-audio":
        result = transcribe_audio(
            audio_path=args.audio_path,
            locale=args.locale,
            engine=args.engine,
            output=args.output,
            auto_init=args.auto_init,
            device=args.device,
            compute_type=args.compute_type,
            device_index=args.device_index,
        )
        if args.report_json:
            if isinstance(result, Path):
                outputs = {"transcript_json": str(result)}
                transcription = read_transcription_payload(result)
            else:
                outputs = {}
                transcription = parse_transcription_payload(result)
            write_execution_report(
                args.report_json,
                command=args.command,
                status="ok",
                started_at=started_at,
                finished_at=utc_timestamp(),
                duration_seconds=time.monotonic() - started_monotonic,
                outputs=outputs,
                transcription=transcription,
            )
        print(result)
        return 0
    if args.command == "render":
        print(
            render_transcript(
                source_ref=args.source_ref,
                transcript_json=args.transcript_json,
                title=args.title,
                language=args.language,
                output=args.output,
            )
        )
        return 0
    if args.command == "init-runtime":
        runtime_dir = args.runtime_dir or default_runtime_dir()
        if args.print_runtime_dir:
            print(runtime_dir)
            return 0
        print(
            initialize_runtime(
                runtime_dir=runtime_dir,
                force_repair=args.force_repair,
            )
        )
        return 0
    if args.command == "check-runtime":
        executable = args.python or selected_runtime_python()
        metadata = inspect_runtime(executable)
        print("\n".join(metadata.as_lines()))
        print("import_health=ok")
        return 0
    if args.command == "install-agent-instructions":
        if args.print_only:
            if args.target or args.force or args.dry_run:
                raise ListenKitError(
                    "--print is mutually exclusive with --target, --force, and --dry-run."
                )
            print(instruction_source().read_text(encoding="utf-8"), end="")
            return 0
        if not args.target:
            raise ListenKitError("--target is required unless --print is used.")
        source, target = install_instructions(
            target=args.target, force=args.force, dry_run=args.dry_run
        )
        if args.dry_run:
            print(f"Source: {source}")
            print(f"Target: {target}")
        else:
            print(target)
        return 0
    if args.command == "doctor":
        print("\n".join(doctor_lines()))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


def _validate_report_destination(args: argparse.Namespace) -> None:
    if _report_conflicts_with_output(args):
        raise ListenKitError(
            "--report-json must not overwrite a Markdown or transcript JSON output."
        )


def _report_conflicts_with_output(args: argparse.Namespace) -> bool:
    report_path = getattr(args, "report_json", None)
    if report_path is None:
        return False
    report = report_path.expanduser().resolve()
    protected: list[Path] = []
    if args.command == "generate-markdown":
        output = args.output.expanduser()
        protected.extend((output, output.with_suffix(".json")))
    elif args.command == "transcribe-audio" and args.output:
        protected.append(args.output.expanduser())
    return any(candidate.resolve() == report for candidate in protected)


def _write_error_report(
    args: argparse.Namespace,
    error: BaseException,
    started_at: str,
    started_monotonic: float,
) -> None:
    report_path = getattr(args, "report_json", None)
    if report_path is None or _report_conflicts_with_output(args):
        return
    try:
        write_execution_report(
            report_path,
            command=args.command,
            status="error",
            started_at=started_at,
            finished_at=utc_timestamp(),
            duration_seconds=time.monotonic() - started_monotonic,
            error=error,
        )
    except Exception as report_error:
        print(
            f"ListenKit could not write execution report {report_path}: {report_error}",
            file=sys.stderr,
        )
