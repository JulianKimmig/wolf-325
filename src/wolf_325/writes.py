"""Low-level validated Modbus writes and read-back verification."""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime
from typing import Any

from .errors import RegisterError, VerificationError
from .register import RegisterDef
from .types import JSONValue


class WriteMixin:
    """Provide safe single-register write primitives to the controller."""

    async def _write_definition(
        self,
        register: RegisterDef,
        value: Any,
        *,
        verify: bool | None,
        allow_dangerous: bool,
    ) -> JSONValue | None:
        """Validate, write, and optionally verify one logical setting."""
        if not register.writable:
            raise RegisterError(f"{register.key} is read-only")
        if register.one_shot:
            raise RegisterError(f"use the dedicated one-shot method for {register.key}")
        if register.dangerous and not allow_dangerous:
            raise RegisterError(
                f"dangerous write to {register.key} requires allow_dangerous=True"
            )
        normalized = register.normalize(value)
        words = register.encode(normalized)
        if len(words) != 1:
            raise RegisterError(
                f"multi-register writes are not implemented for {register.key}"
            )
        await self._write_raw(register, words[0], allow_dangerous=allow_dangerous)
        should_verify = (
            bool(self.config["persistence"]["verify_writes"])
            if verify is None
            else verify
        )
        if register.dangerous:
            should_verify = False
        if not should_verify:
            state = self._values[register.key]
            state.value = normalized
            state.raw = words[0]
            state.available = True
            state.updated_at = datetime.now(UTC).isoformat()
            state.error = None
            await self._emit_update(state)
            return normalized

        attempts = int(self.config["persistence"]["verify_attempts"])
        delay = float(self.config["persistence"]["verify_delay_seconds"])
        actual: JSONValue | None = None
        for attempt in range(attempts):
            await asyncio.sleep(delay if attempt == 0 else min(delay * 2, 1.0))
            state = await self._read_definition(register)
            actual = state.value
            if state.available and self._values_equal(register, actual, normalized):
                return actual
        raise VerificationError(
            f"{register.key}: wrote {normalized!r}, but read back {actual!r} "
            f"after {attempts} attempt(s)"
        )

    async def _write_raw(
        self,
        register: RegisterDef,
        raw_word: int,
        *,
        allow_dangerous: bool,
    ) -> None:
        """Write one raw word after enforcing dangerous-register authorization."""
        if register.dangerous and not allow_dangerous:
            raise RegisterError(
                f"dangerous write to {register.key} requires explicit confirmation"
            )
        await self._request(
            "write_register", register.address, value=int(raw_word) & 0xFFFF
        )

    @staticmethod
    def _values_equal(register: RegisterDef, actual: Any, desired: Any) -> bool:
        """Compare decoded and desired values using register-scale tolerance."""
        if isinstance(actual, str) and actual.startswith("unknown_"):
            return False
        if (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and isinstance(desired, (int, float))
            and not isinstance(desired, bool)
        ):
            return math.isclose(
                float(actual),
                float(desired),
                abs_tol=max(register.scale / 2.0, 1e-6),
            )
        return actual == desired
