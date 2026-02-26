"""Farcaster platform adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from sm_tracker.platforms import AdapterConfigError, PlatformCounts


@dataclass(frozen=True)
class FarcasterAdapter:
    """Fetch Farcaster follower/following counts for one username."""

    username: str
    api_key: str
    name: str = "farcaster"

    def _build_request(self) -> Request:
        username_encoded = quote(self.username, safe="")
        url = f"https://api.warpcast.com/v2/user-by-username?username={username_encoded}"
        return Request(
            url,
            headers={
                # Mirror curl-style request shape to avoid urllib-specific 403s.
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "curl/8.7.1",
            },
        )

    def _request_user_payload(self) -> Mapping[str, Any]:
        request = self._build_request()
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, Mapping):
            return payload
        return {}

    def fetch_counts(self) -> PlatformCounts:
        payload = self._request_user_payload()
        user_data = _extract_user_object(payload)
        follower_count = _extract_count(user_data, "follower_count", "followerCount")
        following_count = _extract_count(user_data, "following_count", "followingCount")
        return PlatformCounts(
            platform=self.name,
            follower_count=follower_count,
            following_count=following_count,
        )


def create_farcaster_adapter(env: Mapping[str, str]) -> FarcasterAdapter:
    """Create a Farcaster adapter from env vars."""
    api_key = env.get("FARCASTER_API_KEY", "").strip()
    if not api_key:
        # Backward-compatible fallback for older configs.
        api_key = env.get("FARCASTER_MNEMONIC", "").strip()
    if not api_key:
        raise AdapterConfigError("Skipping farcaster: missing FARCASTER_API_KEY in environment.")

    username = env.get("FARCASTER_USERNAME", "").strip()
    if not username:
        raise AdapterConfigError("Skipping farcaster: missing FARCASTER_USERNAME in environment.")

    return FarcasterAdapter(username=username, api_key=api_key)


def _extract_user_object(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    result = payload.get("result")
    if isinstance(result, Mapping):
        user = result.get("user")
        if isinstance(user, Mapping):
            return user
    user = payload.get("user")
    if isinstance(user, Mapping):
        return user
    return payload


def _extract_count(data: Mapping[str, Any], snake_key: str, camel_key: str) -> int | None:
    value = data.get(snake_key, data.get(camel_key))
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
