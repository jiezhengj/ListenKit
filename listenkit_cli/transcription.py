from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Mapping

from .asr_device import (
    CudaProbe,
    DeviceSelection,
    cuda_retry_compute_type,
    is_cuda_runtime_failure,
    probe_cuda_devices,
    select_asr_device,
)
from .cuda_runtime import cuda_runtime_environment
from .errors import ListenKitError, RuntimeHealthError
from .health import can_import_faster_whisper
from .mlx_runtime import is_apple_silicon, probe_mlx_runtime
from .platform_paths import (
    huggingface_hub_cache_dir,
    platform_id,
    selected_runtime_python,
)
from .process import run_command
from .runtime import initialize_runtime, prepare_runtime_acceleration, repository_root


def _managed_runtime_python(environment: Mapping[str, str]) -> Path:
    return selected_runtime_python(environment=environment)


def _model_is_cached(model: str, environment: Mapping[str, str]) -> bool:
    model_root = (
        huggingface_hub_cache_dir(environment=environment)
        / f"models--Systran--faster-whisper-{model}"
        / "snapshots"
    )
    if not model_root.is_dir():
        return False
    return any(path.is_file() for path in model_root.glob("*/*model.bin")) or any(
        path.is_file() for path in model_root.glob("*/model.bin")
    )


def _validate_payload(text: str) -> dict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ListenKitError(f"ASR backend returned invalid JSON: {exc}") from exc
    if payload.get("error"):
        error = payload["error"]
        if isinstance(error, dict):
            raise ListenKitError(
                f"ASR backend error: {error.get('type', 'error')}: "
                f"{error.get('message', 'transcription failed')}"
            )
        raise ListenKitError(f"ASR backend error: {error}")
    return payload


def _write_output_atomically(output: Path, text: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text.rstrip("\n") + "\n")
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def transcribe_audio(
    *,
    audio_path: Path,
    locale: str,
    engine: str = "auto",
    output: Path | None = None,
    auto_init: bool = False,
    device: str | None = None,
    compute_type: str | None = None,
    device_index: int | None = None,
    environment: Mapping[str, str] | None = None,
) -> str | Path:
    env = dict(os.environ if environment is None else environment)
    if not audio_path.is_file():
        raise ListenKitError(f"Audio file not found: {audio_path}")
    requested_engine = engine or env.get("LISTENKIT_ASR_ENGINE", "auto")
    if requested_engine not in {"auto", "faster-whisper", "mlx", "apple"}:
        raise ListenKitError(
            f"Unsupported engine: {requested_engine}. Supported engines: "
            "auto, faster-whisper, mlx, apple."
        )
    if requested_engine == "apple":
        if platform_id() == "windows":
            raise ListenKitError("The Apple Speech backend is available only on macOS.")
        helper = Path(
            env.get(
                "APPLE_SPEECH_HELPER",
                str(repository_root() / "tools" / "apple-speech-helper" / "run-apple-speech-helper.sh"),
            )
        )
        result = run_command(
            [helper, "--audio-path", audio_path, "--locale", locale], check=False
        )
    else:
        requested_device = device or env.get("LISTENKIT_ASR_DEVICE", "auto")
        requested_compute_type = compute_type or env.get(
            "LISTENKIT_ASR_COMPUTE_TYPE", "auto"
        )
        explicit = env.get("FASTER_WHISPER_PYTHON")
        python_executable = Path(explicit) if explicit else _managed_runtime_python(env)
        healthy = False
        try:
            healthy = can_import_faster_whisper(python_executable, environment=env)
        except RuntimeHealthError:
            raise
        if not healthy:
            if explicit:
                raise RuntimeHealthError(
                    f"FASTER_WHISPER_PYTHON cannot import faster_whisper: {python_executable}"
                )
            if not auto_init and env.get("LISTENKIT_AUTO_INIT") != "1":
                raise RuntimeHealthError(
                    "faster-whisper is not initialized for ListenKit. Run "
                    ".\\cli\\init-faster-whisper.ps1 on Windows or "
                    "cli/init-faster-whisper.sh on macOS/Linux, or pass --auto-init."
                )
            python_executable = initialize_runtime(
                environment=env,
                require_cuda=requested_device == "cuda",
                prefer_mlx=requested_engine in {"auto", "mlx"},
                require_mlx=requested_engine == "mlx",
            )
        elif not explicit and requested_device != "cpu":
            prepare_runtime_acceleration(
                python_executable,
                environment=env,
                require_cuda=requested_device == "cuda",
                prefer_mlx=requested_engine in {"auto", "mlx"},
                require_mlx=requested_engine == "mlx",
            )

        resolved_engine = _resolve_engine(
            requested_engine,
            python_executable=python_executable,
            requested_device=requested_device,
            environment=env,
        )
        if resolved_engine == "mlx":
            if requested_device not in {"auto", ""} or requested_compute_type not in {
                "auto",
                "",
            }:
                raise ListenKitError(
                    "--device and --compute-type are faster-whisper controls; "
                    "MLX always uses the Apple Silicon Metal GPU."
                )
            result = _run_mlx_whisper_helper(
                python_executable=python_executable,
                audio_path=audio_path,
                locale=locale,
                environment=env,
            )
            stdout = result.stdout or ""
            try:
                payload = _validate_payload(stdout)
            except ListenKitError:
                if result.stderr:
                    raise ListenKitError(f"{result.stderr.strip()}\n{stdout.strip()}")
                raise
            if result.returncode != 0:
                raise ListenKitError(
                    (result.stderr or "").strip()
                    or f"MLX ASR backend failed with exit {result.returncode}"
                )
            payload["device"] = "metal"
            payload["device_index"] = 0
            payload["compute_type"] = payload.get("compute_type", "float16")
            payload["device_selection_reason"] = (
                "Apple Silicon with a ready MLX/Metal runtime"
            )
            stdout = json.dumps(payload, ensure_ascii=False)
        else:
            env = cuda_runtime_environment(python_executable, environment=env)

            helper = Path(
                env.get(
                    "LISTENKIT_FASTER_WHISPER_HELPER",
                    str(repository_root() / "tools" / "faster-whisper" / "transcribe.py"),
                )
            )
            if not helper.is_file():
                raise ListenKitError(f"faster-whisper helper is not installed at: {helper}")
            if _model_is_cached("small", env):
                env.setdefault("HF_HUB_OFFLINE", "1")
                env.setdefault("TRANSFORMERS_OFFLINE", "1")

            selected_index = _selected_device_index(device_index, env)
            probe = (
                CudaProbe(())
                if requested_device == "cpu"
                else probe_cuda_devices(python_executable, environment=env)
            )
            selection = select_asr_device(
                probe,
                requested_device=requested_device,
                requested_compute_type=requested_compute_type,
                requested_device_index=selected_index,
            )
            attempts = _device_attempts(
                selection,
                requested_device=requested_device,
                requested_compute_type=requested_compute_type,
            )
            attempted_labels: list[str] = []
            fallback_reason: str | None = None
            result = None
            payload = None
            for current in attempts:
                result = _run_faster_whisper_helper(
                    python_executable=python_executable,
                    helper=helper,
                    audio_path=audio_path,
                    locale=locale,
                    selection=current,
                    environment=env,
                )
                stdout = result.stdout or ""
                try:
                    payload = _validate_payload(stdout)
                    if result.returncode != 0:
                        raise ListenKitError(
                            (result.stderr or "").strip()
                            or f"ASR backend failed with exit {result.returncode}"
                        )
                except ListenKitError as exc:
                    combined = "\n".join(
                        value
                        for value in (
                            (result.stderr or "").strip(),
                            stdout.strip(),
                            str(exc),
                        )
                        if value
                    )
                    if current.device == "cuda" and is_cuda_runtime_failure(combined):
                        attempted_labels.append(current.label)
                        fallback_reason = _one_line_error(combined)
                        continue
                    if result.stderr:
                        raise ListenKitError(f"{result.stderr.strip()}\n{stdout.strip()}")
                    raise

                payload["device"] = current.device
                payload["device_index"] = current.device_index
                payload["compute_type"] = current.compute_type
                payload["device_selection_reason"] = current.reason
                if current.device_name:
                    payload["device_name"] = current.device_name
                if attempted_labels:
                    payload["fallback_from"] = attempted_labels
                    payload["fallback_reason"] = fallback_reason
                    print(
                        "ListenKit warning: CUDA attempts failed; using CPU INT8. "
                        f"Reason: {fallback_reason}",
                        file=sys.stderr,
                    )
                stdout = json.dumps(payload, ensure_ascii=False)
                break
            else:
                raise ListenKitError(
                    fallback_reason or "All configured faster-whisper device attempts failed."
                )

    if requested_engine == "apple":
        stdout = result.stdout or ""
        try:
            _validate_payload(stdout)
        except ListenKitError:
            if result.stderr:
                raise ListenKitError(f"{result.stderr.strip()}\n{stdout.strip()}")
            raise
        if result.returncode != 0:
            raise ListenKitError(
                (result.stderr or "").strip()
                or f"ASR backend failed with exit {result.returncode}"
            )
    if output is None:
        return stdout.rstrip("\n")
    _write_output_atomically(output, stdout)
    return output


def _selected_device_index(
    explicit: int | None, environment: Mapping[str, str]
) -> int | None:
    if explicit is not None:
        return explicit
    raw = environment.get("LISTENKIT_CUDA_DEVICE_INDEX")
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ListenKitError("LISTENKIT_CUDA_DEVICE_INDEX must be zero or greater.") from exc
    if value < 0 or str(value) != raw.strip():
        raise ListenKitError("LISTENKIT_CUDA_DEVICE_INDEX must be zero or greater.")
    return value


def _device_attempts(
    selection: DeviceSelection,
    *,
    requested_device: str,
    requested_compute_type: str,
) -> list[DeviceSelection]:
    attempts = [selection]
    if selection.device != "cuda":
        return attempts
    if requested_compute_type == "auto":
        retry_type = cuda_retry_compute_type(selection)
        if retry_type:
            attempts.append(
                DeviceSelection(
                    device="cuda",
                    compute_type=retry_type,
                    device_index=selection.device_index,
                    device_name=selection.device_name,
                    reason="lower-memory CUDA retry",
                    supported_compute_types=selection.supported_compute_types,
                )
            )
    if requested_device == "auto":
        attempts.append(
            DeviceSelection(
                device="cpu",
                compute_type="int8",
                reason="CPU fallback after CUDA failure",
            )
        )
    return attempts


def _run_faster_whisper_helper(
    *,
    python_executable: Path,
    helper: Path,
    audio_path: Path,
    locale: str,
    selection: DeviceSelection,
    environment: Mapping[str, str],
):
    return run_command(
        [
            python_executable,
            helper,
            audio_path,
            "--locale",
            locale,
            "--model",
            "small",
            "--device",
            selection.device,
            "--device-index",
            str(selection.device_index),
            "--compute-type",
            selection.compute_type,
            "--beam-size",
            "5",
        ],
        environment=environment,
        check=False,
    )


def _resolve_engine(
    requested_engine: str,
    *,
    python_executable: Path,
    requested_device: str,
    environment: Mapping[str, str],
) -> str:
    if requested_engine == "faster-whisper":
        return requested_engine
    if requested_engine == "mlx":
        if not is_apple_silicon():
            raise ListenKitError("The MLX backend requires Apple Silicon macOS.")
        probe = probe_mlx_runtime(python_executable, environment=environment)
        if not probe.ready:
            raise ListenKitError(
                f"MLX was requested, but its Metal runtime is not ready: {probe.error or 'unknown error'}"
            )
        return requested_engine
    if requested_engine == "auto":
        if requested_device == "auto" and is_apple_silicon():
            probe = probe_mlx_runtime(python_executable, environment=environment)
            if probe.ready:
                return "mlx"
        return "faster-whisper"
    raise ListenKitError(f"Unsupported engine: {requested_engine}")


def _run_mlx_whisper_helper(
    *,
    python_executable: Path,
    audio_path: Path,
    locale: str,
    environment: Mapping[str, str],
):
    helper = Path(
        environment.get(
            "LISTENKIT_MLX_WHISPER_HELPER",
            str(repository_root() / "tools" / "mlx-whisper" / "transcribe.py"),
        )
    )
    if not helper.is_file():
        raise ListenKitError(f"MLX Whisper helper is not installed at: {helper}")
    model = environment.get(
        "LISTENKIT_MLX_MODEL", "mlx-community/whisper-small-mlx"
    )
    return run_command(
        [
            python_executable,
            helper,
            audio_path,
            "--locale",
            locale,
            "--model",
            model,
        ],
        environment=environment,
        check=False,
    )


def _one_line_error(message: str) -> str:
    return " ".join(message.split())[:1000]
