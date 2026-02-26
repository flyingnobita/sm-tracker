"""Mastodon platform adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from mastodon import Mastodon

from sm_tracker.platforms import AdapterConfigError, PlatformCounts


@dataclass(frozen=True)
class MastodonAdapter:
    """Fetch Mastodon follower/following counts for one account."""

    access_token: str
    instance: str
    name: str = "mastodon"

    def _build_client(self) -> Mastodon:
        return Mastodon(
            access_token=self.access_token,
            api_base_url=_normalized_instance_url(self.instance),
        )

    def fetch_counts(self) -> PlatformCounts:
        account = self._build_client().account_verify_credentials()
        follower_count = _extract_count(account, "followers_count")
        following_count = _extract_count(account, "following_count")
        return PlatformCounts(
            platform=self.name,
            follower_count=follower_count,
            following_count=following_count,
        )


def create_mastodon_adapter(env: Mapping[str, str]) -> MastodonAdapter:
    """Create a Mastodon adapter from env vars."""
    access_token = env.get("MASTODON_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise AdapterConfigError("Skipping mastodon: missing MASTODON_ACCESS_TOKEN in environment.")

    instance = env.get("MASTODON_INSTANCE", "").strip()
    if not instance:
        raise AdapterConfigError("Skipping mastodon: missing MASTODON_INSTANCE in environment.")

    return MastodonAdapter(access_token=access_token, instance=instance)


def _normalized_instance_url(instance: str) -> str:
    trimmed = instance.strip()
    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        return trimmed
    return f"https://{trimmed}"


def _extract_count(account: Any, key: str) -> int | None:
    value = getattr(account, key, None)
    if value is None and isinstance(account, Mapping):
        value = account.get(key)
    if value is None:
        return None
    return int(value)
