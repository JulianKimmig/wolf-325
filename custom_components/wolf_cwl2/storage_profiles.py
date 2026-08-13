"""Profile-repository construction and graph validation for HA Store."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

from wolf_325 import MemoryProfileRepository, ProfileRepository

ProfileSaveCallback = Callable[[dict[str, dict[str, object]]], Awaitable[None]]


def build_profile_repository(
    documents: Mapping[str, Mapping[str, object]],
    save_callback: ProfileSaveCallback,
) -> MemoryProfileRepository:
    """Create an in-memory public repository backed by one Store callback.

    Args:
        documents: Initial portable profile document catalogue.
        save_callback: Awaited complete-catalogue persistence callback.

    Returns:
        Public host-neutral profile repository.
    """
    return MemoryProfileRepository(documents, save_callback=save_callback)


async def validate_profile_repository(repository: ProfileRepository) -> None:
    """Resolve every stored profile to reject corrupt inheritance graphs.

    Args:
        repository: Candidate repository loaded from one Store payload.

    Returns:
        None when every profile resolves successfully.
    """
    for name in await repository.list_profiles():
        await repository.load(name)
