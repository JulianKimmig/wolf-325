"""Fresh confirmed-state preflight for cross-register setting relationships."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .catalogue import REGISTERS
from .errors import ValidationError
from .types import JSONScalar
from .validation import affected_relation_groups, validate_cross_settings


class RelationController(Protocol):
    """Describe controller state used for relational preflight reads."""

    _values: Mapping[str, Any]

    async def _read_definition(self, register: Any) -> None:
        """Refresh one canonical register definition."""


async def validate_live_relations(
    controller: RelationController,
    changes: Mapping[str, JSONScalar],
) -> None:
    """Validate affected relations against fresh confirmed peer values.

    Args:
        controller: Controller providing confirmed cached values and reads.
        changes: Canonical normalized values proposed by the caller.

    Raises:
        ValidationError: If a required peer is unavailable after refresh or the
            resulting live group violates a cross-setting invariant.
    """
    for group in affected_relation_groups(changes):
        candidate: dict[str, JSONScalar] = {}
        for key in group:
            if key in changes:
                candidate[key] = changes[key]
                continue
            await controller._read_definition(REGISTERS[key])
            state = controller._values[key]
            if not state.available:
                raise ValidationError(
                    f"{key}: confirmed peer value is unavailable for relational preflight"
                )
            candidate[key] = state.value
        validate_cross_settings(candidate)
