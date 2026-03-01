"""Instagram platform adapter using Graph API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field

from sm_tracker.platforms import AdapterConfigError, PlatformCounts


@dataclass(frozen=True)
class InstagramAdapter:
    """Fetch Instagram follower/following counts via Graph API."""

    account_id: str
    access_token: str = field(repr=False)
    username: str | None = None
    name: str = "instagram"

    def fetch_counts(self) -> PlatformCounts:
        base_url = f"https://graph.facebook.com/v19.0/{self.account_id}"

        if self.username:
            # Business Discovery API for a specific username
            fields = (
                f"business_discovery.username({self.username}){{followers_count,follows_count}}"
            )
        else:
            # Own account insights
            fields = "followers_count,follows_count"

        url = f"{base_url}?fields={fields}&access_token={self.access_token}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise RuntimeError(f"Instagram API Error ({exc.code}): {error_body}") from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch Instagram counts: {exc}") from exc

        if self.username:
            if "business_discovery" not in data:
                raise RuntimeError(f"Missing business_discovery data for '{self.username}'")
            stats = data["business_discovery"]
        else:
            stats = data

        return PlatformCounts(
            platform=self.name,
            follower_count=stats.get("followers_count", 0),
            following_count=stats.get("follows_count", 0),
        )


def create_instagram_adapter(env: Mapping[str, str]) -> InstagramAdapter:
    """Create an Instagram adapter from env vars."""
    account_id = env.get("INSTAGRAM_ACCOUNT_ID", "").strip()
    access_token = env.get("LONG_LIVED_USER_TOKEN", "").strip()
    username = env.get("INSTAGRAM_USERNAME", "").strip() or None

    if not account_id or not access_token:
        raise AdapterConfigError(
            "Skipping instagram: missing INSTAGRAM_ACCOUNT_ID "
            "or LONG_LIVED_USER_TOKEN in environment."
        )

    return InstagramAdapter(
        account_id=account_id,
        access_token=access_token,
        username=username,
    )
