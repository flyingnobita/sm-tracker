"""Bluesky platform adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from atproto import Client  # type: ignore[import-untyped]

from sm_tracker.platforms import AdapterConfigError, PlatformCounts


@dataclass(frozen=True)
class BlueskyAdapter:
    """Fetch Bluesky follower/following counts for one handle."""

    handle: str
    app_password: str | None = None
    name: str = "bluesky"

    def _build_client(self) -> Client:
        return Client()

    def _fetch_profile(self, client: Client) -> Any:
        try:
            return client.get_profile(actor=self.handle)
        except TypeError:
            return client.get_profile(self.handle)

    def fetch_counts(self) -> PlatformCounts:
        client = self._build_client()
        if self.app_password:
            client.login(self.handle, self.app_password)

        profile = self._fetch_profile(client)
        follower_count = _extract_count(profile, "followers_count", "followersCount")
        following_count = _extract_count(profile, "follows_count", "followsCount")
        return PlatformCounts(
            platform=self.name,
            follower_count=follower_count,
            following_count=following_count,
        )


def create_bluesky_adapter(env: Mapping[str, str]) -> BlueskyAdapter:
    """Create a Bluesky adapter from env vars."""
    handle = env.get("BLUESKY_HANDLE", "").strip()
    if not handle:
        raise AdapterConfigError("Skipping bluesky: missing BLUESKY_HANDLE in environment.")

    app_password_raw = env.get("BLUESKY_APP_PASSWORD")
    app_password = app_password_raw.strip() if app_password_raw else None
    return BlueskyAdapter(handle=handle, app_password=app_password)


def _extract_count(profile: Any, snake_key: str, camel_key: str) -> int | None:
    value = getattr(profile, snake_key, None)
    if value is None:
        value = getattr(profile, camel_key, None)

    if value is None and isinstance(profile, Mapping):
        mapped = profile.get(snake_key, profile.get(camel_key))
        value = mapped

    if value is None:
        return None
    return int(value)
