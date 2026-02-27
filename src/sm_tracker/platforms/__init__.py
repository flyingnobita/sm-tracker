"""Platform adapters and shared adapter protocol."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

LOGGER = logging.getLogger(__name__)


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


SUPPORTED_PLATFORM_NAMES: tuple[str, ...] = (
    "bluesky",
    "facebook",
    "farcaster",
    "mastodon",
    "threads",
    "twitter",
    "instagram",
    "youtube",
)


def resolve_adapters(
    selected_platforms: Sequence[str], env: Mapping[str, str] | None = None
) -> tuple[list[PlatformAdapter], list[str]]:
    """Build adapters for selected platform names and collect warnings."""
    from sm_tracker.platforms.bluesky import create_bluesky_adapter
    from sm_tracker.platforms.facebook import create_facebook_adapter
    from sm_tracker.platforms.farcaster import create_farcaster_adapter
    from sm_tracker.platforms.instagram import create_instagram_adapter
    from sm_tracker.platforms.mastodon import create_mastodon_adapter
    from sm_tracker.platforms.threads import create_threads_adapter
    from sm_tracker.platforms.twitter import create_twitter_adapter
    from sm_tracker.platforms.youtube import create_youtube_adapter

    env_map = os.environ if env is None else env
    factories: dict[str, Callable[[Mapping[str, str]], PlatformAdapter]] = {
        "bluesky": create_bluesky_adapter,
        "facebook": create_facebook_adapter,
        "farcaster": create_farcaster_adapter,
        "mastodon": create_mastodon_adapter,
        "threads": create_threads_adapter,
        "twitter": create_twitter_adapter,
        "instagram": create_instagram_adapter,
        "youtube": create_youtube_adapter,
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
            LOGGER.debug("Adapter not configured for %s: %s", name, exc)
            warnings.append(str(exc))

    return adapters, warnings


__all__ = [
    "AdapterConfigError",
    "PlatformAdapter",
    "PlatformCounts",
    "SUPPORTED_PLATFORM_NAMES",
    "resolve_adapters",
]
