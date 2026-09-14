from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .platform_paths import default_runtime_dir


@dataclass(frozen=True)
class CleanResult:
    removed_files: int
    removed_dirs: int
    bytes_freed: int
    dry_run: bool
    targets: tuple[str, ...]


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
            except OSError:
                continue
    except OSError:
        pass
    return total


def clean_workspace(
    repo_root: Path,
    *,
    clean_runtime: bool = False,
    dry_run: bool = False,
    environment: Mapping[str, str] | None = None,
    verbose: bool = False,
) -> CleanResult:
    removed_files = 0
    removed_dirs = 0
    bytes_freed = 0
    logged_targets: list[str] = []

    # 1. Helper App build artifacts
    helper_build = repo_root / "tools" / "apple-speech-helper" / ".build"
    if helper_build.exists():
        size = _dir_size(helper_build)
        bytes_freed += size
        removed_dirs += 1
        logged_targets.append(str(helper_build))
        if verbose or dry_run:
            prefix = "[dry-run] would remove" if dry_run else "removed"
            print(f"ListenKit clean: {prefix} {helper_build} ({size} bytes)")
        if not dry_run:
            shutil.rmtree(helper_build, ignore_errors=True)

    # 2. Pytest cache
    pytest_cache = repo_root / ".pytest_cache"
    if pytest_cache.exists():
        size = _dir_size(pytest_cache)
        bytes_freed += size
        removed_dirs += 1
        logged_targets.append(str(pytest_cache))
        if verbose or dry_run:
            prefix = "[dry-run] would remove" if dry_run else "removed"
            print(f"ListenKit clean: {prefix} {pytest_cache} ({size} bytes)")
        if not dry_run:
            shutil.rmtree(pytest_cache, ignore_errors=True)

    # 3. Recursively find __pycache__, *.pyc, *.pyo, .DS_Store, *.sync-conflict-*
    # Avoid recursing into .git, .specify, or work directories
    ignored_roots = {".git", "work"}

    for dirpath, dirnames, filenames in os.walk(repo_root, topdown=True):
        current_rel = os.path.relpath(dirpath, repo_root)
        first_segment = current_rel.split(os.sep)[0] if current_rel != "." else ""
        if first_segment in ignored_roots:
            dirnames.clear()
            continue

        pycache_dirs = [d for d in dirnames if d == "__pycache__"]
        for pycache in pycache_dirs:
            target_path = Path(dirpath) / pycache
            size = _dir_size(target_path)
            bytes_freed += size
            removed_dirs += 1
            logged_targets.append(str(target_path))
            if verbose or dry_run:
                prefix = "[dry-run] would remove" if dry_run else "removed"
                print(f"ListenKit clean: {prefix} {target_path} ({size} bytes)")
            if not dry_run:
                shutil.rmtree(target_path, ignore_errors=True)
            dirnames.remove(pycache)

        for filename in filenames:
            if (
                filename.endswith((".pyc", ".pyo"))
                or filename == ".DS_Store"
                or ".sync-conflict-" in filename
            ):
                target_path = Path(dirpath) / filename
                try:
                    size = target_path.stat().st_size
                except OSError:
                    size = 0
                bytes_freed += size
                removed_files += 1
                logged_targets.append(str(target_path))
                if verbose or dry_run:
                    prefix = "[dry-run] would remove" if dry_run else "removed"
                    print(f"ListenKit clean: {prefix} {target_path} ({size} bytes)")
                if not dry_run:
                    try:
                        target_path.unlink(missing_ok=True)
                    except OSError:
                        pass

    # 4. Optional managed runtime clean
    if clean_runtime:
        env = os.environ if environment is None else environment
        runtime_dir = default_runtime_dir(environment=env)
        if runtime_dir.exists():
            size = _dir_size(runtime_dir)
            bytes_freed += size
            removed_dirs += 1
            logged_targets.append(str(runtime_dir))
            if verbose or dry_run:
                prefix = "[dry-run] would remove" if dry_run else "removed"
                print(f"ListenKit clean: {prefix} runtime {runtime_dir} ({size} bytes)")
            if not dry_run:
                shutil.rmtree(runtime_dir, ignore_errors=True)

    action = "Would clean" if dry_run else "Cleaned"
    print(
        f"ListenKit: {action} {removed_dirs} directories and {removed_files} files "
        f"({bytes_freed} bytes freed)."
    )
    return CleanResult(
        removed_files=removed_files,
        removed_dirs=removed_dirs,
        bytes_freed=bytes_freed,
        dry_run=dry_run,
        targets=tuple(logged_targets),
    )
