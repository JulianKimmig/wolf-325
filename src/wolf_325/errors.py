"""Domain-specific exceptions raised by the WOLF controller package."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class WolfError(Exception):
    """Base exception for all expected package failures."""


class ConfigError(WolfError):
    """Indicate invalid or inaccessible configuration."""


class ProfileError(WolfError):
    """Indicate an invalid profile or profile dependency."""


class RegisterError(WolfError):
    """Indicate an invalid register name, value, or unsupported write."""


class ValidationError(RegisterError):
    """Indicate a register or cross-register constraint violation."""


class CommunicationError(WolfError):
    """Indicate that no usable Modbus connection is available."""


class RemoteModbusError(CommunicationError):
    """Indicate a Modbus exception returned by the remote appliance."""


class VerificationError(RegisterError):
    """Indicate a completed write whose read-back value did not match."""


class BulkWriteError(RegisterError):
    """Report partial results when one or more bulk writes fail."""

    def __init__(
        self,
        message: str,
        results: Mapping[str, Any],
        errors: Mapping[str, str],
    ) -> None:
        """Initialize a bulk failure.

        Args:
            message: Human-readable summary of the failed operation.
            results: Successfully completed named writes.
            errors: Error messages indexed by failed setting name.
        """
        super().__init__(message)
        self.results = dict(results)
        self.errors = dict(errors)
