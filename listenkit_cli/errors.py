from __future__ import annotations


class ListenKitError(RuntimeError):
    """Expected user-facing ListenKit failure."""


class CommandNotFoundError(ListenKitError):
    """A required external command is unavailable."""


class CommandExecutionError(ListenKitError):
    """An external command returned a non-zero status."""

    def __init__(self, message: str, *, returncode: int = 1, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class RuntimeHealthError(ListenKitError):
    """The selected faster-whisper runtime is missing or unhealthy."""


class RuntimeImportTimeout(RuntimeHealthError):
    """Importing faster-whisper exceeded the configured deadline."""
