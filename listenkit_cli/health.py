from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .errors import CommandExecutionError, RuntimeHealthError, RuntimeImportTimeout
from .process import run_command

EXPECTED_PYTHON = (3, 14)
EXPECTED_FASTER_WHISPER = "1.2.1"
DEFAULT_IMPORT_TIMEOUT_SECONDS = 60

METADATA_CODE = (
    "import importlib.metadata, json, sys; "
    "print(json.dumps({"
    "'python_executable': sys.executable, "
    "'python_version': sys.version.split()[0], "
    "'python_major': sys.version_info.major, "
    "'python_minor': sys.version_info.minor, "
    "'abi_tag': sys.implementation.cache_tag, "
    "'runtime_prefix': sys.prefix, "
    "'faster_whisper_version': importlib.metadata.version('faster-whisper')"
    "}))"
)


@dataclass(frozen=True)
class RuntimeMetadata:
    python_executable: str
    python_version: str
    abi_tag: str
    runtime_prefix: str
    faster_whisper_version: str

    def as_lines(self) -> list[str]:
        return [
            f"python_executable={self.python_executable}",
            f"python_version={self.python_version}",
            f"abi_tag={self.abi_tag}",
            f"runtime_prefix={self.runtime_prefix}",
            f"faster_whisper_version={self.faster_whisper_version}",
        ]


def import_timeout_seconds(environment: Mapping[str, str] | None = None) -> int:
    env = os.environ if environment is None else environment
    raw = env.get(
        "LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS",
        str(DEFAULT_IMPORT_TIMEOUT_SECONDS),
    )
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeHealthError(
            "LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS must be a positive integer."
        ) from exc
    if value <= 0 or str(value) != raw.strip():
        raise RuntimeHealthError(
            "LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS must be a positive integer."
        )
    return value


def python_is_314(executable: Path) -> bool:
    if not executable.is_file():
        return False
    result = run_command(
        [
            executable,
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)",
        ],
        check=False,
        isolate_python=True,
    )
    return result.returncode == 0


def can_import_faster_whisper(
    executable: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> bool:
    if not executable.is_file():
        return False
    timeout = import_timeout_seconds(environment)
    try:
        result = run_command(
            [executable, "-c", "import faster_whisper"],
            environment=environment,
            timeout=timeout,
            check=False,
            isolate_python=True,
        )
    except CommandExecutionError as exc:
        if exc.returncode == 124:
            raise RuntimeImportTimeout(
                f"faster-whisper import timed out after {timeout} seconds: {executable}"
            ) from exc
        raise
    return result.returncode == 0


def inspect_runtime(
    executable: Path,
    *,
    environment: Mapping[str, str] | None = None,
    require_expected_version: bool = True,
) -> RuntimeMetadata:
    import json

    if not executable.is_file():
        raise RuntimeHealthError(f"ListenKit runtime is missing: {executable}")
    try:
        result = run_command(
            [executable, "-c", METADATA_CODE],
            environment=environment,
            isolate_python=True,
        )
        payload = json.loads(result.stdout)
    except (CommandExecutionError, json.JSONDecodeError, KeyError) as exc:
        raise RuntimeHealthError(
            f"ListenKit runtime metadata check failed: {executable}"
        ) from exc

    if (payload.get("python_major"), payload.get("python_minor")) != EXPECTED_PYTHON:
        raise RuntimeHealthError(
            f"ListenKit requires Python 3.14, got {payload.get('python_version', 'unknown')}: "
            f"{executable}"
        )
    if payload.get("abi_tag") != "cpython-314":
        raise RuntimeHealthError(
            f"ListenKit requires ABI cpython-314, got {payload.get('abi_tag', 'unknown')}: "
            f"{executable}"
        )
    installed_version = str(payload.get("faster_whisper_version", ""))
    if require_expected_version and installed_version != EXPECTED_FASTER_WHISPER:
        raise RuntimeHealthError(
            f"ListenKit requires faster-whisper {EXPECTED_FASTER_WHISPER}, "
            f"got {installed_version or 'unknown'}: {executable}"
        )
    runtime_prefix = str(payload.get("runtime_prefix", ""))
    if "/Library/Mobile Documents/" in runtime_prefix.replace("\\", "/"):
        raise RuntimeHealthError(
            f"ListenKit native runtime cannot use an iCloud-backed path: {runtime_prefix}"
        )
    if not can_import_faster_whisper(executable, environment=environment):
        raise RuntimeHealthError(f"faster-whisper cannot be imported from: {executable}")

    return RuntimeMetadata(
        python_executable=str(payload["python_executable"]),
        python_version=str(payload["python_version"]),
        abi_tag=str(payload["abi_tag"]),
        runtime_prefix=runtime_prefix,
        faster_whisper_version=installed_version,
    )
