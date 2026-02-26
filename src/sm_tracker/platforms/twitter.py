"""Twitter/X platform adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import tweepy  # type: ignore[import-untyped]

from sm_tracker.platforms import AdapterConfigError, PlatformCounts


@dataclass(frozen=True)
class TwitterAdapter:
    """Fetch Twitter/X follower/following counts for one handle."""

    handle: str
    bearer_token: str
    name: str = "twitter"

    def _build_client(self) -> tweepy.Client:
        return tweepy.Client(
            bearer_token=self.bearer_token,
            wait_on_rate_limit=True,
        )

    def fetch_counts(self) -> PlatformCounts:
        client = self._build_client()
        response = client.get_user(
            username=self.handle,
            user_fields=["public_metrics"],
        )
        metrics = _extract_public_metrics(response)
        follower_count = _coerce_int(metrics.get("followers_count"))
        following_count = _coerce_int(metrics.get("following_count"))
        return PlatformCounts(
            platform=self.name,
            follower_count=follower_count,
            following_count=following_count,
        )


def create_twitter_adapter(env: Mapping[str, str]) -> TwitterAdapter:
    """Create a Twitter adapter from env vars."""
    bearer_token = env.get("TWITTER_BEARER_TOKEN", "").strip()
    if not bearer_token:
        raise AdapterConfigError("Skipping twitter: missing TWITTER_BEARER_TOKEN in environment.")

    handle = env.get("TWITTER_HANDLE", "").strip()
    if not handle:
        raise AdapterConfigError("Skipping twitter: missing TWITTER_HANDLE in environment.")

    return TwitterAdapter(handle=handle, bearer_token=bearer_token)


def _extract_public_metrics(response: Any) -> Mapping[str, Any]:
    data = getattr(response, "data", None)
    if data is None and isinstance(response, Mapping):
        data = response.get("data")

    if data is None:
        return {}

    metrics = getattr(data, "public_metrics", None)
    if metrics is None and isinstance(data, Mapping):
        maybe_metrics = data.get("public_metrics")
        if isinstance(maybe_metrics, Mapping):
            metrics = maybe_metrics

    if isinstance(metrics, Mapping):
        return metrics
    return {}


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
