"""Async Modbus control for WOLF CWL-2-325 ventilation appliances."""

from .catalogue import (
    READ_BLOCKS,
    REGISTER_ALIASES,
    REGISTER_LIST,
    REGISTERS,
    resolve_register_name,
)
from .config import (
    DEFAULT_CONFIG,
    ConfigStore,
    atomic_json_write,
    atomic_json_write_sync,
    read_json,
)
from .controller import WolfCWL2
from .derived_values import VIRTUAL_VALUES, VirtualValueDef, resolve_value_name
from .errors import (
    BulkWriteError,
    CommunicationError,
    ConfigError,
    ProfileError,
    RegisterError,
    RemoteModbusError,
    ValidationError,
    VerificationError,
    WolfError,
)
from .example_profiles import example_profile_documents
from .profile_engine import ProfileRepository
from .profiles import (
    MemoryProfileRepository,
    ProfileChanges,
    ProfileLoader,
    ResolvedProfile,
    SavedProfile,
)
from .register import ReadBlock, RegisterDef
from .state import ValueState
from .runtime_config import ConfigRepository, RuntimeConfigStore
from .validation import normalize_settings

__all__ = [
    "DEFAULT_CONFIG",
    "READ_BLOCKS",
    "REGISTER_ALIASES",
    "REGISTER_LIST",
    "REGISTERS",
    "BulkWriteError",
    "CommunicationError",
    "ConfigError",
    "ConfigStore",
    "ConfigRepository",
    "MemoryProfileRepository",
    "ProfileError",
    "ProfileChanges",
    "ProfileLoader",
    "ProfileRepository",
    "ReadBlock",
    "RegisterDef",
    "RegisterError",
    "RemoteModbusError",
    "ResolvedProfile",
    "RuntimeConfigStore",
    "SavedProfile",
    "ValidationError",
    "ValueState",
    "VIRTUAL_VALUES",
    "VirtualValueDef",
    "VerificationError",
    "WolfCWL2",
    "WolfError",
    "atomic_json_write",
    "atomic_json_write_sync",
    "example_profile_documents",
    "normalize_settings",
    "read_json",
    "resolve_register_name",
    "resolve_value_name",
]
