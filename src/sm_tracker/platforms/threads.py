"""Threads platform adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from threads import ThreadsClient

from sm_tracker.platforms import AdapterConfigError, PlatformCounts


@dataclass(frozen=True)
class ThreadsAdapter:
    """Fetch Threads follower/following counts for one user id."""

    access_token: str
    user_id: str
    name: str = "threads"

    def _build_client(self) -> ThreadsClient:
        return ThreadsClient(access_token=self.access_token)

    def fetch_counts(self) -> PlatformCounts:
        client = self._build_client()
        try:
            user_insights = client.insights.get_user_insights(self.user_id)
            profile = client.users.get(user_id=self.user_id)
        finally:
            client.close()

        follower_count = _extract_metric(user_insights, "followers_count")
        following_count = _extract_count(profile, "following_count")
        return PlatformCounts(
            platform=self.name,
            follower_count=follower_count,
            following_count=following_count,
        )


def create_threads_adapter(env: Mapping[str, str]) -> ThreadsAdapter:
    """Create a Threads adapter from env vars."""
    access_token = env.get("THREADS_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise AdapterConfigError("Skipping threads: missing THREADS_ACCESS_TOKEN in environment.")

    user_id = env.get("THREADS_USER_ID", "").strip()
    if not user_id:
        raise AdapterConfigError("Skipping threads: missing THREADS_USER_ID in environment.")

    return ThreadsAdapter(access_token=access_token, user_id=user_id)


def _extract_count(profile: Any, key: str) -> int:
    value = getattr(profile, key, None)
    if value is None and isinstance(profile, Mapping):
        value = profile.get(key)
    if value is None:
        return 0
    return int(value)


def _extract_metric(user_insights: Any, key: str) -> int:
    get_metric = getattr(user_insights, "get_metric", None)
    if callable(get_metric):
        value = get_metric(key)
        if value is None:
            return 0
        return int(value)
    return 0
