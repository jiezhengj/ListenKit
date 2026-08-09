from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .asr_device import CudaProbe, probe_cuda_devices
from .cuda_runtime import install_managed_cuda_dependencies, nvidia_driver_available
from .errors import ListenKitError, RuntimeHealthError
from .health import EXPECTED_FASTER_WHISPER, inspect_runtime, python_is_314
from .mlx_runtime import (
    install_managed_mlx_dependencies,
    is_apple_silicon,
    probe_mlx_runtime,
)
from .platform_paths import default_runtime_dir, platform_id, runtime_python_path


@dataclass(frozen=True)
class PythonCommand:
    executable: str
    prefix_arguments: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeAcceleration:
    backend: str
    ready: bool
    preparation_attempted: bool
    message: str


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _candidate_commands(
    *, platform: str | None = None, environment: Mapping[str, str] | None = None
) -> list[PythonCommand]:
    env = os.environ if environment is None else environment
    override = env.get("LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON")
    if override:
        return [PythonCommand(override)]

    if platform_id(platform) == "windows":
        return [
            PythonCommand("py", ("-3.14",)),
            PythonCommand("python3.14"),
            PythonCommand("python"),
        ]
    return [
        PythonCommand("/opt/homebrew/bin/python3.14"),
        PythonCommand("/opt/homebrew/opt/python@3.14/bin/python3.14"),
        PythonCommand("/usr/local/bin/python3.14"),
        PythonCommand("python3.14"),
        PythonCommand("python3"),
    ]


def _resolve_command(command: PythonCommand) -> PythonCommand | None:
    value = command.executable
    if os.path.dirname(value):
        path = Path(value).expanduser()
        if not path.is_file():
            return None
        return PythonCommand(str(path), command.prefix_arguments)
    resolved = shutil.which(value)
    if not resolved:
        return None
    return PythonCommand(resolved, command.prefix_arguments)


def _command_is_python314(command: PythonCommand) -> bool:
    result = subprocess.run(
        [
            command.executable,
            *command.prefix_arguments,
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def find_bootstrap_python314(
    *, platform: str | None = None, environment: Mapping[str, str] | None = None
) -> PythonCommand:
    for candidate in _candidate_commands(platform=platform, environment=environment):
        resolved = _resolve_command(candidate)
        if resolved and _command_is_python314(resolved):
            return resolved
    raise ListenKitError(
        "Python 3.14 is required. Install it or set "
        "LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON."
    )


def initialize_runtime(
    *,
    runtime_dir: Path | None = None,
    platform: str | None = None,
    environment: Mapping[str, str] | None = None,
    force_repair: bool = False,
    require_cuda: bool = False,
    prefer_mlx: bool = True,
    require_mlx: bool = False,
) -> Path:
    env = dict(os.environ if environment is None else environment)
    target_dir = runtime_dir or default_runtime_dir(platform=platform, environment=env)
    if "/Library/Mobile Documents/" in str(target_dir).replace("\\", "/"):
        raise RuntimeHealthError(
            f"Refusing to create ListenKit's native runtime in an iCloud-backed path: {target_dir}"
        )
    executable = runtime_python_path(target_dir, platform=platform)

    runtime_is_healthy = False
    if executable.is_file():
        if not python_is_314(executable):
            raise RuntimeHealthError(
                f"Existing ListenKit runtime does not use Python 3.14: {executable}"
            )
        if not force_repair:
            try:
                inspect_runtime(executable, environment=env)
                runtime_is_healthy = True
            except RuntimeHealthError:
                pass
    if not executable.is_file():
        bootstrap = find_bootstrap_python314(platform=platform, environment=env)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                bootstrap.executable,
                *bootstrap.prefix_arguments,
                "-m",
                "venv",
                str(target_dir),
            ],
            check=False,
        )
        if result.returncode != 0:
            raise ListenKitError(f"Failed to create ListenKit runtime at: {target_dir}")

    if not runtime_is_healthy:
        requirements = repository_root() / "requirements-faster-whisper.txt"
        for arguments, description in (
            (["-m", "pip", "install", "--upgrade", "pip"], "upgrade pip"),
            (["-m", "pip", "install", "-r", str(requirements)], "install requirements"),
        ):
            result = subprocess.run([str(executable), *arguments], check=False)
            if result.returncode != 0:
                raise ListenKitError(f"Failed to {description} in: {executable}")

    metadata = inspect_runtime(executable, environment=env)
    if metadata.faster_whisper_version != EXPECTED_FASTER_WHISPER:
        raise RuntimeHealthError(
            f"ListenKit requires faster-whisper {EXPECTED_FASTER_WHISPER}: {executable}"
        )
    prepare_runtime_acceleration(
        executable,
        platform=platform,
        environment=env,
        require_cuda=require_cuda,
        prefer_mlx=prefer_mlx,
        require_mlx=require_mlx,
    )
    return executable


def prepare_runtime_acceleration(
    executable: Path,
    *,
    platform: str | None = None,
    environment: Mapping[str, str] | None = None,
    require_cuda: bool = False,
    prefer_mlx: bool = True,
    require_mlx: bool = False,
    machine: str | None = None,
) -> RuntimeAcceleration:
    env = dict(os.environ if environment is None else environment)
    current_platform = platform_id(platform)
    if current_platform == "macos":
        if require_cuda:
            raise ListenKitError("CUDA was requested, but CUDA is not available on macOS.")
        if prefer_mlx and is_apple_silicon(platform=platform, machine=machine):
            initial_probe = probe_mlx_runtime(executable, environment=env)
            if initial_probe.ready:
                return RuntimeAcceleration(
                    backend="mlx-metal",
                    ready=True,
                    preparation_attempted=False,
                    message="MLX can access the Apple Silicon Metal GPU",
                )
            installation = install_managed_mlx_dependencies(
                executable,
                environment=env,
                platform=platform,
                machine=machine,
            )
            final_probe = (
                probe_mlx_runtime(executable, environment=env)
                if installation.succeeded
                else initial_probe
            )
            if final_probe.ready:
                return RuntimeAcceleration(
                    backend="mlx-metal",
                    ready=True,
                    preparation_attempted=installation.attempted,
                    message="Managed MLX/Metal runtime is ready",
                )
            detail = (
                final_probe.error
                or installation.message
                or "MLX probe could not access Metal"
            )
            if require_mlx:
                raise ListenKitError(f"MLX/Metal preparation failed: {detail}")
            print(
                "ListenKit warning: Apple Silicon detected, but MLX/Metal "
                f"preparation did not complete: {detail}",
                file=sys.stderr,
            )
            return RuntimeAcceleration(
                backend="apple-accelerate",
                ready=True,
                preparation_attempted=installation.attempted,
                message=f"MLX unavailable; using Apple Accelerate CPU backend: {detail}",
            )
        if require_mlx:
            raise ListenKitError("MLX was requested, but this Mac is not Apple Silicon.")
        return RuntimeAcceleration(
            backend="apple-accelerate",
            ready=True,
            preparation_attempted=False,
            message=(
                "CTranslate2 uses its Apple Accelerate CPU backend; its macOS wheel "
                "does not provide a Metal/MPS GPU backend"
            ),
        )
    if current_platform not in {"windows", "linux"}:
        return RuntimeAcceleration(
            backend="cpu",
            ready=True,
            preparation_attempted=False,
            message="No managed GPU backend is available on this platform",
        )
    if not nvidia_driver_available(env):
        if require_cuda:
            raise ListenKitError("CUDA was requested, but no NVIDIA GPU driver was detected.")
        return RuntimeAcceleration(
            backend="cpu",
            ready=True,
            preparation_attempted=False,
            message="No NVIDIA GPU driver was detected",
        )

    initial_probe = probe_cuda_devices(executable, environment=env)
    if _cuda_probe_ready(initial_probe):
        return RuntimeAcceleration(
            backend="cuda",
            ready=True,
            preparation_attempted=False,
            message="CUDA runtime is already ready",
        )

    installation = install_managed_cuda_dependencies(executable, environment=env)
    final_probe = (
        probe_cuda_devices(executable, environment=env)
        if installation.succeeded
        else initial_probe
    )
    if _cuda_probe_ready(final_probe):
        return RuntimeAcceleration(
            backend="cuda",
            ready=True,
            preparation_attempted=installation.attempted,
            message="Managed CUDA runtime is ready",
        )

    detail = final_probe.error or installation.message or "CUDA probe found no device"
    if require_cuda:
        raise ListenKitError(f"CUDA preparation failed: {detail}")
    print(
        f"ListenKit warning: NVIDIA GPU detected, but CUDA preparation did not complete: {detail}",
        file=sys.stderr,
    )
    return RuntimeAcceleration(
        backend="cuda",
        ready=False,
        preparation_attempted=installation.attempted,
        message=detail,
    )


def _cuda_probe_ready(probe: CudaProbe) -> bool:
    return bool(probe.devices) and not probe.error
