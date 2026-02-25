"""Platform adapters and shared adapter protocol."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


class AdapterConfigError(ValueError):
    """Raised when adapter configuration is missing or invalid."""


@dataclass(frozen=True)
class PlatformCounts:
    """Follower/following count payload returned by an adapter."""

    platform: str
    follower_count: int | None
    following_count: int | None


class PlatformAdapter(Protocol):
    """Common interface each platform adapter must implement."""

    @property
    def name(self) -> str:
        """Platform identifier (for example, `bluesky`)."""
        ...

    def fetch_counts(self) -> PlatformCounts:
        """Fetch the latest counts for the configured account."""
        ...


def resolve_adapters(
    selected_platforms: Sequence[str], env: Mapping[str, str] | None = None
) -> tuple[list[PlatformAdapter], list[str]]:
    """Build adapters for selected platform names and collect warnings."""
    from sm_tracker.platforms.bluesky import create_bluesky_adapter

    env_map = os.environ if env is None else env
    factories = {
        "bluesky": create_bluesky_adapter,
    }
    adapters: list[PlatformAdapter] = []
    warnings: list[str] = []
    seen: set[str] = set()

    for name in selected_platforms:
        if name in seen:
            continue
        seen.add(name)

        factory = factories.get(name)
        if factory is None:
            warnings.append(f"Skipping unsupported platform: {name}")
            continue

        try:
            adapters.append(factory(env_map))
        except AdapterConfigError as exc:
            warnings.append(str(exc))

    return adapters, warnings


__all__ = [
    "AdapterConfigError",
    "PlatformAdapter",
    "PlatformCounts",
    "resolve_adapters",
]

