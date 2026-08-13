"""Behavior tests for the complete register catalogue and value codecs."""

from __future__ import annotations

import math

import pytest

from wolf_325 import (
    READ_BLOCKS,
    REGISTER_ALIASES,
    REGISTER_LIST,
    REGISTERS,
    RegisterDef,
    RegisterError,
    ValidationError,
    resolve_register_name,
)


def test_catalogue_has_all_reference_registers_and_unique_keys() -> None:
    """The packaged catalogue must retain all 154 guide values exactly once."""
    assert len(REGISTER_LIST) == 154
    assert len(REGISTERS) == 154
    assert set(REGISTERS) == {register.key for register in REGISTER_LIST}
    assert sum(register.table == "input" for register in REGISTER_LIST) == 76
    assert sum(register.table == "holding" for register in REGISTER_LIST) == 78
    assert sum(register.writable for register in REGISTER_LIST) == 78
    assert sum(register.restorable for register in REGISTER_LIST) == 69


def test_read_blocks_cover_each_polled_definition_once() -> None:
    """Each polled value must belong to one block of its table and tier."""
    for register in REGISTER_LIST:
        if register.poll == "never":
            continue
        owners = [
            block
            for block in READ_BLOCKS
            if block.table == register.table
            and block.tier == register.poll
            and block.start <= register.address
            and register.address + register.count <= block.start + block.count
        ]
        assert len(owners) == 1, register.key


def test_register_alias_resolution_is_normalized_and_helpful() -> None:
    """Aliases and friendly punctuation resolve while unknown names fail."""
    assert resolve_register_name("Fan Level") == "remote_ventilation_level"
    assert resolve_register_name("supply-temperature-c") == "supply_temperature_c"
    assert resolve_register_name("airflow") == REGISTER_ALIASES["airflow"]
    with pytest.raises(RegisterError, match="possible matches"):
        resolve_register_name("supply_temperature")
    with pytest.raises(RegisterError, match="unknown"):
        resolve_register_name("nothing_like_a_register")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(0x0000, 0.0), (0x007B, 12.3), (0xFF85, -12.3)],
)
def test_signed_temperature_scaling(raw: int, expected: float) -> None:
    """Signed scaled temperatures decode positive, zero, and negative words."""
    assert REGISTERS["supply_temperature_c"].decode([raw]) == expected


@pytest.mark.parametrize(
    ("key", "raw", "expected"),
    [
        ("supply_relative_humidity_pct", 27, 27),
        ("exhaust_relative_humidity_pct", 33, 33),
    ],
)
def test_fan_humidity_uses_whole_percent_values(
    key: str, raw: int, expected: int
) -> None:
    """Decode fan humidity words as the whole percentages shown by the appliance."""
    assert REGISTERS[key].decode([raw]) == expected


def test_version_serial_counter_and_raw_word_codecs() -> None:
    """Multi-word identity and counter codecs preserve their documented format."""
    assert REGISTERS["base_software_version"].decode(
        [(ord("S") << 8) | 1, (2 << 8) | 3, 45]
    ) == "S1.02.03.0045"
    assert REGISTERS["base_hardware_version"].decode([0x0203]) == "H2.3"
    assert REGISTERS["serial_number"].decode(
        [0x1234, 0x5678, 0x9012]
    ) == "123456789012"
    assert REGISTERS["operating_time_hours"].decode([0x0001, 0x0002]) == 65538
    assert REGISTERS["appliance_date_raw"].decode([7, 8]) == [7, 8]


def test_enum_codec_accepts_labels_aliases_and_raw_numbers() -> None:
    """Enum input canonicalizes supported user forms and reports unknown raw data."""
    register = REGISTERS["flow_control_method"]
    assert register.normalize("constant flow") == "constant_flow"
    assert register.normalize(1) == "constant_flow"
    assert register.encode("constant-flow") == [1]
    assert register.decode([99]) == "unknown_99"
    with pytest.raises(ValidationError):
        register.normalize(True)
    with pytest.raises(ValidationError):
        register.normalize("unsupported")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, True), (1, True), ("enabled", True), (False, False), ("off", False)],
)
def test_boolean_codec_normalizes_supported_forms(value: object, expected: bool) -> None:
    """Boolean settings accept explicit conventional forms only."""
    register = REGISTERS["bypass_boost"]
    assert register.normalize(value) is expected
    assert register.encode(value) == [int(expected)]
    assert register.decode([int(expected)]) is expected


@pytest.mark.parametrize("value", [2, -1, "sometimes", object()])
def test_boolean_codec_rejects_ambiguous_forms(value: object) -> None:
    """Boolean normalization rejects values that could hide caller mistakes."""
    with pytest.raises(ValidationError):
        REGISTERS["bypass_boost"].normalize(value)


def test_packed_calendar_codecs_accept_supported_input_shapes() -> None:
    """Clock and date codecs canonicalize strings, mappings, and pairs."""
    time = REGISTERS["device_time"]
    date = REGISTERS["device_date_month_day"]
    weekday = REGISTERS["device_weekday_second"]
    assert time.normalize({"hour": 7, "minute": 5}) == "07:05"
    assert time.encode([23, 59]) == [0x173B]
    assert time.decode([0x173B]) == "23:59"
    assert time.decode([0x1860]).startswith("invalid_")
    assert date.normalize([2, 29]) == "02-29"
    assert date.encode("12-31") == [0x0C1F]
    assert weekday.normalize({"weekday": 7, "second": 59}) == "7:59"
    assert weekday.encode("1:02") == [0x0102]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("device_time", "24:00"),
        ("device_time", "12:60"),
        ("device_date_month_day", "02-30"),
        ("device_weekday_second", "8:00"),
    ],
)
def test_packed_calendar_codecs_reject_invalid_values(key: str, value: str) -> None:
    """Clock and calendar bounds are enforced before any write occurs."""
    with pytest.raises(ValidationError):
        REGISTERS[key].normalize(value)


def test_numeric_constraints_include_steps_extras_and_finite_values() -> None:
    """Numeric codecs enforce device ranges without losing documented extras."""
    holiday = REGISTERS["flow_preset_holiday_m3h"]
    low = REGISTERS["flow_preset_low_m3h"]
    threshold = REGISTERS["bypass_indoor_threshold_c"]
    assert holiday.normalize(0) == 0
    assert low.normalize(150) == 150
    assert threshold.encode(20.5) == [205]
    assert threshold.decode([205]) == 20.5
    for invalid in (0, 49, 151):
        with pytest.raises(ValidationError):
            low.normalize(invalid)
    with pytest.raises(ValidationError, match="step"):
        threshold.normalize(20.3)
    for invalid in (math.inf, math.nan, True):
        with pytest.raises(ValidationError):
            threshold.normalize(invalid)


def test_codec_rejects_invalid_word_shapes_and_read_only_encoding() -> None:
    """Malformed wire data and writes to identity codecs fail explicitly."""
    with pytest.raises(ValueError, match="expected 3 words"):
        REGISTERS["serial_number"].decode([1])
    with pytest.raises(RegisterError, match="read-only"):
        REGISTERS["serial_number"].normalize("123")
    custom = RegisterDef("too_large", 1, "holding", "test", writable=True)
    with pytest.raises(ValidationError, match="16-bit"):
        custom.encode(65536)
