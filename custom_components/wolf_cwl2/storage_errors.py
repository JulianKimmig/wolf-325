"""Sanitized Home Assistant Store failures shared by lifecycle owners."""

from __future__ import annotations


class EntryStoreError(RuntimeError):
    """Report unsafe, corrupt, or unverifiable per-entry persistence."""

    def __init__(self, message: str, *, fault: str | None = None) -> None:
        """Initialize one sanitized persistence error and optional repair type.

        Args:
            message: Operator-safe error without stored data or identifiers.
            fault: Stable actionable repair category, when applicable.
        """
        super().__init__(message)
        self.fault = fault
