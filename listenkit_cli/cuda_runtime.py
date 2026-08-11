from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .errors import CommandExecutionError, ListenKitError
from .platform_paths import platform_id
from .process import find_command, run_command

CUDA_LIBRARY_DIRS_CODE = r"""
import json
import site
from pathlib import Path

directories = []
for root_text in site.getsitepackages():
    root = Path(root_text) / "nvidia"
    for component in ("cublas", "cudnn", "cuda_runtime"):
        for leaf in ("bin", "lib"):
            candidate = root / component / leaf
            if candidate.is_dir():
                directories.append(str(candidate.resolve()))
print(json.dumps(directories))
""".strip()


@dataclass(frozen=True)
class CudaDependencyInstall:
    attempted: bool
    succeeded: bool
    message: str


def nvidia_driver_available(
    environment: Mapping[str, str] | None = None,
) -> bool:
    env = os.environ if environment is None else environment
    executable = find_command("nvidia-smi", environment=env)
    if not executable:
        return False
    try:
        result = run_command(
            [executable, "--query-gpu=index", "--format=csv,noheader,nounits"],
            environment=env,
            timeout=10,
            check=False,
        )
    except CommandExecutionError:
        return False
    return result.returncode == 0 and any(
        line.strip().isdigit() for line in result.stdout.splitlines()
    )


def cuda_library_dirs(
    python_executable: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    env = dict(os.environ if environment is None else environment)
    try:
        result = run_command(
            [python_executable, "-c", CUDA_LIBRARY_DIRS_CODE],
            environment=env,
            timeout=20,
            check=False,
            isolate_python=True,
        )
    except ListenKitError:
        return ()
    if result.returncode != 0:
        return ()
    try:
        raw_directories = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ()
    directories: list[Path] = []
    for raw in raw_directories:
        candidate = Path(str(raw))
        if candidate.is_dir() and candidate not in directories:
            directories.append(candidate)
    return tuple(directories)


def cuda_runtime_environment(
    python_executable: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if environment is None else environment)
    directories = cuda_library_dirs(python_executable, environment=env)
    if not directories:
        return env
    rendered = [str(path) for path in directories]
    env["LISTENKIT_CUDA_LIBRARY_DIRS"] = os.pathsep.join(rendered)
    variable = "PATH" if platform_id() == "windows" else "LD_LIBRARY_PATH"
    current = env.get(variable, "")
    env[variable] = os.pathsep.join([*rendered, *([current] if current else [])])
    return env


def install_managed_cuda_dependencies(
    python_executable: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> CudaDependencyInstall:
    env = dict(os.environ if environment is None else environment)
    if platform_id() not in {"windows", "linux"}:
        return CudaDependencyInstall(False, False, "CUDA is not supported on this platform")
    if env.get("LISTENKIT_CUDA_AUTO_PREPARE", "1") == "0":
        return CudaDependencyInstall(False, False, "CUDA auto-preparation was disabled")
    if not nvidia_driver_available(env):
        return CudaDependencyInstall(False, False, "No NVIDIA CUDA driver was detected")

    requirements = (
        Path(__file__).resolve().parents[1] / "requirements-faster-whisper-cuda.txt"
    )
    print(
        "ListenKit: preparing managed CUDA 12 cuBLAS and cuDNN 9 dependencies...",
        file=sys.stderr,
    )
    result = run_command(
        [python_executable, "-m", "pip", "install", "-r", requirements],
        environment=env,
        check=False,
        isolate_python=True,
    )
    if result.stdout:
        print(result.stdout.rstrip(), file=sys.stderr)
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        return CudaDependencyInstall(
            True,
            False,
            f"pip exited with status {result.returncode} while installing CUDA dependencies",
        )
    return CudaDependencyInstall(
        True,
        True,
        "installed managed CUDA 12 cuBLAS and cuDNN 9 dependencies",
    )
