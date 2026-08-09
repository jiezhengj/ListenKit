from __future__ import annotations

import json
import os
import platform as host_platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .errors import CommandExecutionError
from .platform_paths import platform_id
from .process import run_command

MLX_PROBE_TIMEOUT_SECONDS = 30

MLX_PROBE_CODE = """
import importlib.metadata
import json
try:
    import mlx.core as mx
    import mlx_whisper
    payload = {
        "mlx_version": importlib.metadata.version("mlx"),
        "mlx_whisper_version": importlib.metadata.version("mlx-whisper"),
        "metal_available": bool(mx.metal.is_available()),
        "default_device": str(mx.default_device()),
    }
    if not payload["metal_available"]:
        payload["error"] = "MLX imported, but no Metal device is available"
    print(json.dumps(payload))
except Exception as exc:
    print(json.dumps({"error": f"{exc.__class__.__name__}: {exc}"}))
""".strip()


@dataclass(frozen=True)
class MlxProbe:
    ready: bool
    metal_available: bool = False
    mlx_version: str | None = None
    mlx_whisper_version: str | None = None
    default_device: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class MlxDependencyInstall:
    attempted: bool
    succeeded: bool
    message: str


def is_apple_silicon(
    *, platform: str | None = None, machine: str | None = None
) -> bool:
    architecture = (machine or host_platform.machine()).casefold()
    return platform_id(platform) == "macos" and architecture in {"arm64", "aarch64"}


def probe_mlx_runtime(
    python_executable: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> MlxProbe:
    env = dict(os.environ if environment is None else environment)
    try:
        result = run_command(
            [python_executable, "-c", MLX_PROBE_CODE],
            environment=env,
            timeout=MLX_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except CommandExecutionError as exc:
        return MlxProbe(False, error=str(exc))
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return MlxProbe(False, error=detail or f"MLX probe exited with {result.returncode}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return MlxProbe(False, error=f"MLX probe returned invalid JSON: {exc}")
    error = payload.get("error")
    metal_available = bool(payload.get("metal_available"))
    return MlxProbe(
        ready=metal_available and not error,
        metal_available=metal_available,
        mlx_version=_optional_text(payload.get("mlx_version")),
        mlx_whisper_version=_optional_text(payload.get("mlx_whisper_version")),
        default_device=_optional_text(payload.get("default_device")),
        error=_optional_text(error),
    )


def install_managed_mlx_dependencies(
    python_executable: Path,
    *,
    environment: Mapping[str, str] | None = None,
    platform: str | None = None,
    machine: str | None = None,
) -> MlxDependencyInstall:
    env = dict(os.environ if environment is None else environment)
    if not is_apple_silicon(platform=platform, machine=machine):
        return MlxDependencyInstall(False, False, "MLX requires Apple Silicon macOS")
    if env.get("LISTENKIT_MLX_AUTO_PREPARE", "1") == "0":
        return MlxDependencyInstall(False, False, "MLX auto-preparation was disabled")
    requirements = Path(__file__).resolve().parents[1] / "requirements-mlx-whisper.txt"
    print("ListenKit: preparing MLX/Metal acceleration for Apple Silicon...", file=sys.stderr)
    result = run_command(
        [python_executable, "-m", "pip", "install", "-r", requirements],
        environment=env,
        check=False,
    )
    if result.stdout:
        print(result.stdout.rstrip(), file=sys.stderr)
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        return MlxDependencyInstall(
            True,
            False,
            f"pip exited with status {result.returncode} while installing MLX dependencies",
        )
    return MlxDependencyInstall(True, True, "installed mlx-whisper and MLX Metal runtime")


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
