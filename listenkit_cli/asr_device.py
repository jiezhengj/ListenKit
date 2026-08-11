from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .cuda_runtime import cuda_runtime_environment
from .errors import CommandExecutionError, ListenKitError
from .process import find_command, run_command

CUDA_PROBE_TIMEOUT_SECONDS = 20
CUDA_FLOAT16_FREE_MIB = 3072

ALLOWED_DEVICES = {"auto", "cpu", "cuda"}
ALLOWED_COMPUTE_TYPES = {
    "auto",
    "int8",
    "int8_float32",
    "int8_float16",
    "float16",
    "float32",
    "bfloat16",
}
CPU_COMPUTE_TYPES = {"int8", "int8_float32", "float32"}

CUDA_PROBE_CODE = """
import json
try:
    import ctypes
    import os
    import ctranslate2
    import sys
    dll_directory_handles = []
    library_dirs = [
        value for value in os.environ.get("LISTENKIT_CUDA_LIBRARY_DIRS", "").split(os.pathsep)
        if value
    ]
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        for directory in library_dirs:
            try:
                dll_directory_handles.append(os.add_dll_directory(directory))
            except OSError:
                pass
    count = ctranslate2.get_cuda_device_count()
    devices = []
    for index in range(count):
        devices.append({
            "index": index,
            "supported_compute_types": sorted(
                ctranslate2.get_supported_compute_types("cuda", index)
            ),
        })
    libraries = {}
    if count:
        if sys.platform == "win32":
            loader = ctypes.WinDLL
            names = ("cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_9.dll")
        else:
            loader = ctypes.CDLL
            names = ("libcublas.so.12", "libcublasLt.so.12", "libcudnn.so.9")
        for name in names:
            candidates = [os.path.join(directory, name) for directory in library_dirs]
            candidates.append(name)
            libraries[name] = False
            for candidate in candidates:
                try:
                    loader(candidate)
                    libraries[name] = True
                    break
                except OSError:
                    pass
    required = tuple(
        name for name in libraries
        if "cublas" in name.casefold() or "cudnn" in name.casefold()
    )
    missing = [name for name in required if not libraries[name]]
    payload = {"devices": devices, "libraries": libraries}
    if missing:
        payload["error"] = "Required CUDA libraries are not loadable: " + ", ".join(missing)
    print(json.dumps(payload))
except Exception as exc:
    print(json.dumps({"devices": [], "error": f"{exc.__class__.__name__}: {exc}"}))
""".strip()


@dataclass(frozen=True)
class CudaDevice:
    index: int
    supported_compute_types: frozenset[str]
    name: str | None = None
    uuid: str | None = None
    total_memory_mib: int | None = None
    free_memory_mib: int | None = None
    compute_capability: float | None = None


@dataclass(frozen=True)
class CudaProbe:
    devices: tuple[CudaDevice, ...]
    error: str | None = None
    libraries: tuple[tuple[str, bool], ...] = ()


@dataclass(frozen=True)
class DeviceSelection:
    device: str
    compute_type: str
    device_index: int = 0
    device_name: str | None = None
    reason: str = ""
    supported_compute_types: frozenset[str] = frozenset()

    @property
    def label(self) -> str:
        return f"{self.device}/{self.compute_type}"


def probe_cuda_devices(
    python_executable: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> CudaProbe:
    env = cuda_runtime_environment(
        python_executable,
        environment=os.environ if environment is None else environment,
    )
    try:
        result = run_command(
            [python_executable, "-c", CUDA_PROBE_CODE],
            environment=env,
            timeout=CUDA_PROBE_TIMEOUT_SECONDS,
            check=False,
            isolate_python=True,
        )
    except CommandExecutionError as exc:
        return CudaProbe((), str(exc))
    if result.returncode != 0:
        message = (result.stderr or "").strip()
        return CudaProbe((), message or f"CUDA probe exited with {result.returncode}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return CudaProbe((), f"CUDA probe returned invalid JSON: {exc}")

    smi_devices = _query_nvidia_smi(environment=env)
    devices = []
    for raw_device in payload.get("devices", []):
        index = int(raw_device["index"])
        smi = smi_devices.get(index, {})
        devices.append(
            CudaDevice(
                index=index,
                supported_compute_types=frozenset(
                    str(value) for value in raw_device.get("supported_compute_types", [])
                ),
                name=smi.get("name"),
                uuid=smi.get("uuid"),
                total_memory_mib=_optional_int(smi.get("total_memory_mib")),
                free_memory_mib=_optional_int(smi.get("free_memory_mib")),
                compute_capability=_optional_float(smi.get("compute_capability")),
            )
        )
    libraries = tuple(
        sorted(
            (str(name), bool(available))
            for name, available in payload.get("libraries", {}).items()
        )
    )
    return CudaProbe(tuple(devices), payload.get("error"), libraries)


def select_asr_device(
    probe: CudaProbe,
    *,
    requested_device: str = "auto",
    requested_compute_type: str = "auto",
    requested_device_index: int | None = None,
) -> DeviceSelection:
    if requested_device not in ALLOWED_DEVICES:
        raise ListenKitError("--device must be one of: auto, cpu, cuda")
    if requested_compute_type not in ALLOWED_COMPUTE_TYPES:
        raise ListenKitError(
            "--compute-type must be one of: auto, int8, int8_float32, "
            "int8_float16, float16, float32, bfloat16"
        )
    if requested_device_index is not None and requested_device_index < 0:
        raise ListenKitError("--device-index must be zero or greater.")

    if requested_device == "cpu":
        if requested_device_index is not None:
            raise ListenKitError("--device-index is only valid with auto or cuda.")
        return _cpu_selection(requested_compute_type, "CPU was explicitly selected")

    candidates = list(probe.devices)
    if requested_device_index is not None:
        candidates = [device for device in candidates if device.index == requested_device_index]
        if not candidates and requested_device == "cuda":
            raise ListenKitError(
                f"CUDA device index {requested_device_index} is not available."
            )

    if candidates and probe.error:
        if requested_device == "cuda":
            raise ListenKitError(f"CUDA runtime is not ready: {probe.error}")
        if requested_compute_type not in {"auto", *CPU_COMPUTE_TYPES}:
            raise ListenKitError(
                f"Compute type {requested_compute_type} requires CUDA, but {probe.error}"
            )
        return _cpu_selection(requested_compute_type, probe.error)

    if not candidates:
        if requested_device == "cuda":
            detail = f" ({probe.error})" if probe.error else ""
            raise ListenKitError(f"CUDA was requested but no usable CUDA device was detected{detail}.")
        if requested_compute_type not in {"auto", *CPU_COMPUTE_TYPES}:
            raise ListenKitError(
                f"Compute type {requested_compute_type} requires a compatible CUDA device."
            )
        reason = probe.error or "no CUDA device was detected"
        return _cpu_selection(requested_compute_type, reason)

    device = max(
        candidates,
        key=lambda value: (
            value.free_memory_mib if value.free_memory_mib is not None else -1,
            -value.index,
        ),
    )
    supported = device.supported_compute_types

    if requested_compute_type != "auto":
        if requested_compute_type not in supported:
            raise ListenKitError(
                f"CUDA device {device.index} does not support compute type "
                f"{requested_compute_type}. Supported: {', '.join(sorted(supported)) or 'unknown'}"
            )
        return DeviceSelection(
            device="cuda",
            compute_type=requested_compute_type,
            device_index=device.index,
            device_name=device.name,
            reason="CUDA and compute type were explicitly selected",
            supported_compute_types=supported,
        )

    compute_type = _automatic_cuda_compute_type(device)
    if not compute_type:
        if requested_device == "cuda":
            raise ListenKitError(
                f"CUDA device {device.index} has no supported ListenKit compute type."
            )
        return _cpu_selection("auto", "CUDA device has no efficient supported compute type")

    return DeviceSelection(
        device="cuda",
        compute_type=compute_type,
        device_index=device.index,
        device_name=device.name,
        reason="compatible CUDA device and compute type detected",
        supported_compute_types=supported,
    )


def cuda_retry_compute_type(selection: DeviceSelection) -> str | None:
    if selection.device != "cuda":
        return None
    for candidate in ("int8_float16", "int8", "int8_float32"):
        if candidate != selection.compute_type and candidate in selection.supported_compute_types:
            return candidate
    return None


def is_cuda_runtime_failure(message: str) -> bool:
    normalized = message.casefold()
    markers = (
        "cuda",
        "cublas",
        "cudnn",
        "nvrtc",
        "nvidia",
        "out of memory",
        "memory allocation",
        "not enough memory",
        "driver version",
        "compute capability",
    )
    return any(marker in normalized for marker in markers)


def _automatic_cuda_compute_type(device: CudaDevice) -> str | None:
    supported = device.supported_compute_types
    if (
        device.free_memory_mib is not None
        and device.free_memory_mib < CUDA_FLOAT16_FREE_MIB
        and "int8_float16" in supported
    ):
        return "int8_float16"
    if "float16" in supported:
        return "float16"
    if "int8_float16" in supported:
        return "int8_float16"
    if "int8_float32" in supported:
        return "int8_float32"
    if "float32" in supported:
        return "float32"
    return None


def _cpu_selection(compute_type: str, reason: str) -> DeviceSelection:
    selected = "int8" if compute_type == "auto" else compute_type
    if selected not in CPU_COMPUTE_TYPES:
        raise ListenKitError(
            f"Compute type {selected} is not supported by ListenKit's CPU policy."
        )
    return DeviceSelection(
        device="cpu",
        compute_type=selected,
        reason=reason,
        supported_compute_types=frozenset(CPU_COMPUTE_TYPES),
    )


def _query_nvidia_smi(
    *, environment: Mapping[str, str] | None = None
) -> dict[int, dict[str, object]]:
    env = os.environ if environment is None else environment
    executable = find_command("nvidia-smi", environment=env)
    if not executable:
        return {}
    fields = ("index", "name", "uuid", "memory.total", "memory.free", "compute_cap")
    try:
        result = _run_nvidia_smi_query(executable, fields, env)
    except CommandExecutionError:
        return {}
    has_compute_capability = result.returncode == 0
    if result.returncode != 0:
        fields = fields[:-1]
        try:
            result = _run_nvidia_smi_query(executable, fields, env)
        except CommandExecutionError:
            return {}
        if result.returncode != 0:
            return {}
    devices: dict[int, dict[str, object]] = {}
    for line in result.stdout.splitlines():
        values = [value.strip() for value in line.split(",")]
        if len(values) != len(fields):
            continue
        try:
            index = int(values[0])
        except ValueError:
            continue
        devices[index] = {
            "name": values[1],
            "uuid": values[2],
            "total_memory_mib": values[3],
            "free_memory_mib": values[4],
            "compute_capability": values[5] if has_compute_capability else None,
        }
    return devices


def _run_nvidia_smi_query(
    executable: str,
    fields: tuple[str, ...],
    environment: Mapping[str, str] | None,
):
    return run_command(
        [
            executable,
            f"--query-gpu={','.join(fields)}",
            "--format=csv,noheader,nounits",
        ],
        environment=environment,
        timeout=10,
        check=False,
    )


def _optional_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _optional_float(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
