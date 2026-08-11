from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

from .errors import CommandExecutionError, CommandNotFoundError
from .platform_paths import platform_id


def find_command(
    name: str,
    *,
    environment: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> str | None:
    env = os.environ if environment is None else environment
    resolved = shutil.which(name, path=env.get("PATH", ""))
    if resolved:
        return resolved
    if platform_id(platform) == "macos" and os.path.dirname(name) == "":
        for prefix in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
            candidate = prefix / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    if platform_id(platform) == "windows" and os.path.dirname(name) == "":
        normalized = name.casefold()
        if normalized in {"nvidia-smi", "nvidia-smi.exe"}:
            system_root = env.get("SystemRoot") or env.get("SYSTEMROOT")
            if system_root:
                candidate = Path(system_root) / "System32" / "nvidia-smi.exe"
                if candidate.is_file():
                    return str(candidate)
        executable_names = {
            "ffmpeg": "ffmpeg.exe",
            "ffmpeg.exe": "ffmpeg.exe",
            "ffprobe": "ffprobe.exe",
            "ffprobe.exe": "ffprobe.exe",
            "yt-dlp": "yt-dlp.exe",
            "yt-dlp.exe": "yt-dlp.exe",
        }
        executable_name = executable_names.get(normalized)
        local_app_data = env.get("LOCALAPPDATA")
        if executable_name and local_app_data:
            candidate = (
                Path(local_app_data)
                / "Microsoft"
                / "WinGet"
                / "Links"
                / executable_name
            )
            if candidate.is_file():
                return str(candidate)
    return None


def require_command(name: str) -> str:
    resolved = find_command(name)
    if resolved:
        return resolved
    suffix = ".exe" if os.name == "nt" and not name.lower().endswith(".exe") else ""
    raise CommandNotFoundError(
        f"Missing required command: {name}{suffix}. Install it and ensure it is available on PATH."
    )


def run_command(
    args: Sequence[str | os.PathLike[str]],
    *,
    cwd: Path | None = None,
    environment: Mapping[str, str] | None = None,
    timeout: int | float | None = None,
    check: bool = True,
    capture: bool = True,
    isolate_python: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [os.fspath(value) for value in args]
    child_environment = (
        isolated_python_environment(environment)
        if isolate_python
        else dict(os.environ if environment is None else environment)
    )
    child_environment.setdefault("PYTHONUTF8", "1")
    child_environment.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        result = subprocess.run(
            command,
            cwd=os.fspath(cwd) if cwd else None,
            env=child_environment,
            timeout=timeout,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError as exc:
        raise CommandNotFoundError(f"Command not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CommandExecutionError(
            f"Command timed out after {timeout} seconds: {command[0]}",
            returncode=124,
            stderr=_coerce_text(exc.stderr),
        ) from exc

    if check and result.returncode != 0:
        stderr = (result.stderr or "").strip()
        message = f"Command failed with exit {result.returncode}: {command[0]}"
        if stderr:
            message = f"{message}\n{stderr}"
        raise CommandExecutionError(message, returncode=result.returncode, stderr=stderr)
    return result


def isolated_python_environment(
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    child_environment = dict(os.environ if environment is None else environment)
    child_environment.pop("PYTHONHOME", None)
    child_environment.pop("PYTHONPATH", None)
    child_environment.setdefault("PYTHONUTF8", "1")
    child_environment.setdefault("PYTHONIOENCODING", "utf-8")
    return child_environment


def _coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
