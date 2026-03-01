"""YouTube platform adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from sm_tracker.platforms import AdapterConfigError, BaseAdapter, PlatformCounts
from sm_tracker.platforms.utils import extract_int


@dataclass(frozen=True)
class YouTubeAdapter(BaseAdapter):
    """Fetch YouTube subscriber counts for a channel handle or ID."""

    api_key: str = field(repr=False)
    handle: str | None = None
    channel_id: str | None = None

    @property
    def name(self) -> str:
        return "youtube"

    def __post_init__(self) -> None:
        if not self.handle and not self.channel_id:
            raise ValueError("YouTubeAdapter requires either a handle or a channel_id.")

    def _build_url(self) -> str:
        base_url = "https://www.googleapis.com/youtube/v3/channels?part=statistics&key="
        api_key_encoded = quote(self.api_key, safe="")

        if self.channel_id:
            channel_id_encoded = quote(self.channel_id, safe="")
            return f"{base_url}{api_key_encoded}&id={channel_id_encoded}"

        if self.handle:
            handle_encoded = quote(self.handle, safe="")
            return f"{base_url}{api_key_encoded}&forHandle={handle_encoded}"

        return ""

    def _build_request(self) -> Request:
        url = self._build_url()
        return Request(
            url,
            headers={"User-Agent": "sm-tracker"},
        )

    def _request_channel_payload(self) -> Mapping[str, Any]:
        request = self._build_request()
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, Mapping):
            return payload
        return {}

    def fetch_counts(self) -> PlatformCounts:
        payload = self._request_channel_payload()
        items = payload.get("items")

        follower_count: int | None = None

        if isinstance(items, list) and len(items) > 0:
            first_item = items[0]
            if isinstance(first_item, Mapping):
                statistics = first_item.get("statistics")
                if isinstance(statistics, Mapping):
                    follower_count = extract_int(statistics, "subscriberCount")

        return PlatformCounts(
            platform=self.name,
            follower_count=follower_count,
            following_count=None,
        )

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> YouTubeAdapter:
        """Create a YouTube adapter from env vars."""
        api_key = env.get("YOUTUBE_API_KEY", "").strip()
        if not api_key:
            raise AdapterConfigError("Skipping youtube: missing YOUTUBE_API_KEY in environment.")

        channel_id = env.get("YOUTUBE_CHANNEL_ID", "").strip()
        handle = env.get("YOUTUBE_HANDLE", "").strip()

        if not channel_id and not handle:
            raise AdapterConfigError(
                "Skipping youtube: missing YOUTUBE_CHANNEL_ID or YOUTUBE_HANDLE in environment."
            )

        return cls(
            api_key=api_key,
            channel_id=channel_id if channel_id else None,
            handle=handle if handle else None,
        )
