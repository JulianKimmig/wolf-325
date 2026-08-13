# Physical CWL-2-325 validation

## Purpose

This workflow proves behavior that simulated tests cannot: gateway reachability,
unit routing, PDU address offset, the physical register set, real decoding, and
optional-hardware availability. It is required before declaring the reference
port complete. Package unit/coverage tests remain a separate required gate.

The connected Waveshare gateway endpoint belongs only in the local untracked
configuration. The reference configuration uses Modbus TCP port 502, device/unit
ID 20, address offset 0, and 19,200 baud with even parity on the gateway's RS485
side. Confirm the appliance and gateway settings before treating a read failure
as a library defect.

## Safety boundary

Start and complete the catalogue audit in read-only mode. Do not restore desired
state, run reconciliation, reset the filter/appliance, or write communication,
airflow, frost, bypass, heater, or standby settings as part of read validation.
The configuration used for the audit must have an empty `desired` object.

The gateway web password is operationally sensitive and is not test output. Do
not record it in snapshots, logs, fixtures, commits, or issue text.

## Gates

1. Run the complete package test suite with the repository's `uv` environment.
   Codec, catalogue, config/profile, controller, and CLI tests must pass before
   using their decoded values as device evidence.
2. Create a local, untracked schema-version-1 configuration for
   `<gateway-host>:502`, unit 20, `modbus_tcp`, and offset 0. Keep `desired` empty
   and enable holding plus extension reads.
3. Establish a read-only connection and read the identity values first:
   `base_software_version`, `base_hardware_version`, `appliance_type`, and
   `serial_number`. Values must decode plausibly and the serial must have 12
   digits.
4. Read every catalogue definition, including input and holding values and
   definitions with normal `poll=never`. A normal tiered snapshot is not enough
   for this gate because one-shot status registers are intentionally excluded
   from polling. The audit must continue after optional protocol exceptions.
5. Record one result for every catalogue key in exactly one class:
   `available`, `unsupported_optional`, or `failed`. Include table, documented
   address, raw word(s), decoded value/unit when available, and the error for
   unavailable values. The union of the three classes must equal the catalogue;
   no key may be silently omitted.
6. Required definitions must be available. `unsupported_optional` is acceptable
   for definitions marked optional when the device returns an illegal-address
   response or a repeatable connected zero-word response. The latter must be
   isolated by individual reads with supported adjacent definitions still
   readable. A timeout, disconnect, decode error, or rejection/short response
   of a required address is a failure. See
   [decision 001](../decisions/001-optional-zero-word-responses.md).
7. Sanity-check at least supply/exhaust temperatures, actual and setpoint
   airflows, fan speeds/statuses, ventilation mode, filter status, device ID,
   version strings, serial number, and counters. Temperatures must not be shifted
   by a factor of ten, and adjacent values must not show evidence of a one-word
   address shift.
8. If required values consistently appear shifted or are rejected, repeat the
   read-only audit with offset `-1` and compare the full results. Change the
   default only when the evidence supports it; `0` remains the documented
   baseline.
9. Retain a redacted summary containing the package version/commit, UTC time,
   endpoint category only, unit ID, offset, catalogue count, counts by
   result class, failed keys, optional unsupported keys, and the sanity-check
   outcome. Raw live data containing the device serial should remain untracked.

## Completion evidence

The physical-device requirement is satisfied only when the audit accounts for
all package catalogue keys, no required key failed, every available value
decoded without error, the sanity checks passed, and the command exited
successfully. A successful TCP connection, a handful of plausible reads, or an
`available-only` snapshot does not satisfy the requirement.

After the read-only gate passes, write-path confidence comes from unit tests.
Any optional live write test requires the user's explicit selection of safe
settings and expected restore values; it is not implicitly authorized by this
workflow.

## Verified endpoint baseline

On 2026-07-18 the private gateway endpoint was verified in TCP-server,
Modbus-TCP-to-RTU mode on port 502 with RS485 at 19,200 baud, 8 data bits, even
parity, and 1 stop bit. A read-only unit-20, offset-0 audit accounted for all
154 catalogue entries: 153 available, one unsupported optional
(`extension_hardware_version` at input 4503), zero decode errors, zero failed
keys, and zero required failures. Normal block polling also completed with all
required polled values available. The unredacted report, including the serial
number, remains outside the repository.

On 2026-08-11 a fresh read-only recheck was attempted with an empty desired
state. The private gateway was unreachable: one of 154 definitions was
attempted before connection failure, so the catalogue and normal-poll tests
both failed without issuing a write. The temporary raw report was deleted and
only this aggregate result was retained. The successful 2026-07-18 baseline is
historical evidence, not a substitute for a passing release-day connection.

On 2026-08-13 the gateway at its changed private address passed the complete
read-only gate with an empty desired state and restoration/reconciliation
disabled. Both hardware tests passed in 15.27 seconds at unit 20 and offset 0.
All 154 definitions were accounted for: 153 available, one unsupported optional
(`extension_hardware_version`), zero decode errors, zero failed keys, and zero
required failures. Version and 12-digit identity shapes, temperatures,
airflows, fan speeds/statuses, ventilation/filter statuses, and counters passed
the redacted plausibility checks. The raw report and disposable configuration
were removed after deriving this aggregate; no device write was authorized or
issued.
