"""Load the complete generated WOLF/Brink register and polling catalogue."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, Final

from .codecs import slug
from .errors import RegisterError
from .register import ReadBlock, RegisterDef


def _load_catalogue() -> dict[str, Any]:
    """Read packaged register metadata generated from the reference implementation."""
    resource = files("wolf_325").joinpath("register_catalogue.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def _register_from_json(item: dict[str, Any]) -> RegisterDef:
    """Convert one serialized register record into immutable typed metadata."""
    enum = item.get("enum")
    item["enum"] = None if enum is None else {int(key): value for key, value in enum.items()}
    item["extra_values"] = tuple(item.get("extra_values", ()))
    return RegisterDef(**item)


_CATALOGUE = _load_catalogue()
REGISTER_LIST: Final[list[RegisterDef]] = [
    _register_from_json(item) for item in _CATALOGUE["registers"]
]
REGISTERS: Final[dict[str, RegisterDef]] = {
    register.key: register for register in REGISTER_LIST
}
if len(REGISTERS) != len(REGISTER_LIST):
    raise RuntimeError("duplicate register key")
REGISTER_ALIASES: Final[dict[str, str]] = dict(_CATALOGUE["aliases"])
READ_BLOCKS: Final[tuple[ReadBlock, ...]] = tuple(
    ReadBlock(**item) for item in _CATALOGUE["read_blocks"]
)


def resolve_register_name(name: str) -> str:
    """Resolve a canonical or aliased name and provide close-match hints on failure."""
    key = slug(name)
    key = REGISTER_ALIASES.get(key, key)
    if key not in REGISTERS:
        close = sorted(candidate for candidate in REGISTERS if key in candidate or candidate in key)
        hint = f"; possible matches: {', '.join(close[:8])}" if close else ""
        raise RegisterError(f"unknown register/setting {name!r}{hint}")
    return key
