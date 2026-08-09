from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping

VENV_NAME = "cpython-314"


def platform_id(platform: str | None = None) -> str:
    value = platform or sys.platform
    if value == "win32":
        return "windows"
    if value == "darwin":
        return "macos"
    if value.startswith("linux"):
        return "linux"
    return value


def default_runtime_dir(
    *,
    platform: str | None = None,
    environment: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    env = os.environ if environment is None else environment
    override = env.get("LISTENKIT_FASTER_WHISPER_VENV_DIR")
    if override:
        return Path(override).expanduser()

    current_platform = platform_id(platform)
    if current_platform == "windows":
        local_app_data = env.get("LOCALAPPDATA")
        if not local_app_data:
            raise ValueError(
                "LOCALAPPDATA is not set. Set LISTENKIT_FASTER_WHISPER_VENV_DIR explicitly."
            )
        return Path(local_app_data) / "ListenKit" / "venvs" / VENV_NAME

    home_path = home or Path.home()
    return home_path / "Library" / "Caches" / "ListenKit" / "venvs" / VENV_NAME


def runtime_python_path(runtime_dir: Path, *, platform: str | None = None) -> Path:
    if platform_id(platform) == "windows":
        return runtime_dir / "Scripts" / "python.exe"
    return runtime_dir / "bin" / "python"


def selected_runtime_python(
    *,
    platform: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> Path:
    env = os.environ if environment is None else environment
    explicit_python = env.get("LISTENKIT_FASTER_WHISPER_VENV_PYTHON")
    if explicit_python:
        return Path(explicit_python).expanduser()
    return runtime_python_path(
        default_runtime_dir(platform=platform, environment=env),
        platform=platform,
    )


def huggingface_hub_cache_dir(
    *, environment: Mapping[str, str] | None = None, home: Path | None = None
) -> Path:
    env = os.environ if environment is None else environment
    if env.get("HF_HUB_CACHE"):
        return Path(env["HF_HUB_CACHE"]).expanduser()
    if env.get("HF_HOME"):
        return Path(env["HF_HOME"]).expanduser() / "hub"
    return (home or Path.home()) / ".cache" / "huggingface" / "hub"
