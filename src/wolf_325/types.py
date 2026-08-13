"""Shared type aliases for JSON values and Modbus register classification."""

from __future__ import annotations

from typing import Literal, TypeAlias

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
TableName: TypeAlias = Literal["input", "holding"]
PollTier: TypeAlias = Literal["fast", "slow", "static", "never"]
