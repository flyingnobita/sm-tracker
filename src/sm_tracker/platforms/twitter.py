"""Twitter/X platform adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import tweepy  # type: ignore[import-untyped]

from sm_tracker.platforms import AdapterConfigError, BaseAdapter, PlatformCounts
from sm_tracker.platforms.utils import coerce_int


@dataclass(frozen=True)
class TwitterAdapter(BaseAdapter):
    """Fetch Twitter/X follower/following counts for one handle."""

    handle: str
    consumer_key: str = field(repr=False)
    consumer_secret: str = field(repr=False)
    access_token: str = field(repr=False)
    access_token_secret: str = field(repr=False)

    @property
    def name(self) -> str:
        return "twitter"

    def _build_client(self) -> tweepy.Client:
        return tweepy.Client(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
            wait_on_rate_limit=True,
        )

    def fetch_counts(self) -> PlatformCounts:
        client = self._build_client()
        response = client.get_user(
            username=self.handle,
            user_fields=["public_metrics"],
            user_auth=True,
        )
        metrics = _extract_public_metrics(response)
        follower_count = coerce_int(metrics.get("followers_count"))
        following_count = coerce_int(metrics.get("following_count"))
        return PlatformCounts(
            platform=self.name,
            follower_count=follower_count,
            following_count=following_count,
        )

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> TwitterAdapter:
        """Create a Twitter adapter from env vars."""
        consumer_key = env.get("TWITTER_CONSUMER_KEY", "").strip()
        if not consumer_key:
            raise AdapterConfigError(
                "Skipping twitter: missing TWITTER_CONSUMER_KEY in environment."
            )

        consumer_secret = env.get("TWITTER_CONSUMER_SECRET", "").strip()
        if not consumer_secret:
            raise AdapterConfigError(
                "Skipping twitter: missing TWITTER_CONSUMER_SECRET in environment."
            )

        access_token = env.get("TWITTER_ACCESS_TOKEN", "").strip()
        if not access_token:
            raise AdapterConfigError(
                "Skipping twitter: missing TWITTER_ACCESS_TOKEN in environment."
            )

        access_token_secret = env.get("TWITTER_ACCESS_TOKEN_SECRET", "").strip()
        if not access_token_secret:
            raise AdapterConfigError(
                "Skipping twitter: missing TWITTER_ACCESS_TOKEN_SECRET in environment."
            )

        handle = env.get("TWITTER_HANDLE", "").strip()
        if not handle:
            raise AdapterConfigError("Skipping twitter: missing TWITTER_HANDLE in environment.")

        return cls(
            handle=handle,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )


def _extract_public_metrics(response: Any) -> Mapping[str, Any]:
    """Extract the public_metrics dict from a tweepy Response, supporting attr and dict access."""
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
