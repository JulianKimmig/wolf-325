"""Fixtures scoped to WOLF CWL-2 Home Assistant component tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from .fakes import FakeGateway


@pytest.fixture
def fake_gateway(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeGateway]:
    """Replace only the external PyModbus constructor with a deterministic fake.

    Args:
        monkeypatch: Pytest external-boundary patch helper.

    Yields:
        Configurable fake gateway used by the real public client transport.
    """
    gateway = FakeGateway()
    monkeypatch.setattr(
        "wolf_325.transport.AsyncModbusTcpClient",
        gateway.construct_client,
    )
    yield gateway
