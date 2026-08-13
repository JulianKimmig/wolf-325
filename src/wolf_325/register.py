"""Register metadata objects that delegate engineering-value codec behavior."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .types import JSONScalar, JSONValue, PollTier, TableName


@dataclass(frozen=True, slots=True)
class RegisterDef:
    """Describe one logical Modbus value and its wire representation."""

    key: str
    address: int
    table: TableName
    description: str
    codec: str = "u16"
    count: int = 1
    scale: float = 1.0
    unit: str | None = None
    enum: Mapping[int, str] | None = None
    enum_aliases: Mapping[str, str] = field(default_factory=dict)
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    extra_values: tuple[float, ...] = ()
    writable: bool = False
    restorable: bool = False
    dangerous: bool = False
    one_shot: bool = False
    optional: bool = False
    poll: PollTier = "slow"

    def enum_reverse(self) -> dict[str, int]:
        """Return normalized enum labels and aliases mapped to raw values."""
        from .codecs import enum_reverse

        return enum_reverse(self)

    def normalize(self, value: Any) -> JSONScalar:
        """Validate a user value and return its canonical JSON scalar."""
        from .codecs import normalize_value

        return normalize_value(self, value)

    def encode(self, value: Any) -> list[int]:
        """Validate and encode a user value into 16-bit register words."""
        from .codecs import encode_value

        return encode_value(self, value)

    def decode(self, words: Sequence[int]) -> JSONValue:
        """Decode register words into a JSON-compatible engineering value."""
        from .codecs import decode_value

        return decode_value(self, words)

    def raw_json(self, words: Sequence[int]) -> JSONValue:
        """Represent raw words as a scalar for one word or list for many."""
        return int(words[0]) if len(words) == 1 else [int(word) for word in words]


@dataclass(frozen=True, slots=True)
class ReadBlock:
    """Describe one contiguous Modbus read request used during polling."""

    table: TableName
    tier: PollTier
    start: int
    count: int
    optional: bool = False
    extension_only: bool = False
