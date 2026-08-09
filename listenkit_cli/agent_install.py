from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .errors import ListenKitError
from .runtime import repository_root


def instruction_source() -> Path:
    return repository_root() / "adapters" / "agent" / "listenkit-agent-instructions.md"


def resolve_target(raw_target: Path) -> Path:
    target = raw_target.expanduser()
    if target.is_dir():
        return target.resolve() / "listenkit-agent-instructions.md"
    parent = target.parent
    if not parent.is_dir():
        raise ListenKitError(f"Target parent directory does not exist: {parent}")
    return parent.resolve() / target.name


def install_instructions(
    *, target: Path, force: bool = False, dry_run: bool = False
) -> tuple[Path, Path]:
    source = instruction_source()
    if not source.is_file():
        raise ListenKitError(f"ListenKit agent instructions source is missing: {source}")
    destination = resolve_target(target)
    if dry_run:
        return source, destination
    if destination.exists() and not force:
        raise ListenKitError(
            f"Target already exists: {destination}\nUse --force to overwrite it."
        )
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(source.read_text(encoding="utf-8"))
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return source, destination
