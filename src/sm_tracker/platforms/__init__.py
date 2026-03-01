"""Platform adapters and shared adapter protocol."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger(__name__)


class AdapterConfigError(ValueError):
    """Raised when adapter configuration is missing or invalid."""


@dataclass(frozen=True)
class PlatformCounts:
    """Follower/following count payload returned by an adapter."""

    platform: str
    follower_count: int | None
    following_count: int | None


class BaseAdapter(ABC):
    """Common abstract base class each platform adapter must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform identifier (for example, `bluesky`)."""

    @abstractmethod
    def fetch_counts(self) -> PlatformCounts:
        """Fetch the latest counts for the configured account."""

    @classmethod
    @abstractmethod
    def from_env(cls, env: Mapping[str, str]) -> BaseAdapter:
        """Create an adapter instance from environment variables."""


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
) -> tuple[list[BaseAdapter], list[str]]:
    """Build adapters for selected platform names and collect warnings."""
    from sm_tracker.platforms.bluesky import BlueskyAdapter
    from sm_tracker.platforms.facebook import FacebookAdapter
    from sm_tracker.platforms.farcaster import FarcasterAdapter
    from sm_tracker.platforms.instagram import InstagramAdapter
    from sm_tracker.platforms.mastodon import MastodonAdapter
    from sm_tracker.platforms.threads import ThreadsAdapter
    from sm_tracker.platforms.twitter import TwitterAdapter
    from sm_tracker.platforms.youtube import YouTubeAdapter

    env_map = os.environ if env is None else env
    factories: dict[str, Any] = {
        "bluesky": BlueskyAdapter,
        "facebook": FacebookAdapter,
        "farcaster": FarcasterAdapter,
        "mastodon": MastodonAdapter,
        "threads": ThreadsAdapter,
        "twitter": TwitterAdapter,
        "instagram": InstagramAdapter,
        "youtube": YouTubeAdapter,
    }
    adapters: list[BaseAdapter] = []
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
            adapters.append(factory.from_env(env_map))
        except AdapterConfigError as exc:
            LOGGER.debug("Adapter not configured for %s: %s", name, exc)
            warnings.append(str(exc))

    return adapters, warnings


__all__ = [
    "AdapterConfigError",
    "BaseAdapter",
    "PlatformCounts",
    "SUPPORTED_PLATFORM_NAMES",
    "resolve_adapters",
]
