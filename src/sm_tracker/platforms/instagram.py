"""Instagram platform adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import instaloader

from sm_tracker.platforms import AdapterConfigError, PlatformCounts


@dataclass(frozen=True)
class InstagramAdapter:
    """Fetch Instagram follower/following counts for a public profile."""

    username: str
    name: str = "instagram"

    def fetch_counts(self) -> PlatformCounts:
        # Using instaloader to fetch public profile info
        # See: https://instaloader.github.io/module/structures.html#instaloader.Profile
        L = instaloader.Instaloader(quiet=True)
        L.context._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }
        )
        try:
            profile = instaloader.Profile.from_username(L.context, self.username)
        except Exception as exc:  # instaloader often throws on rate limits or missing profiles
            # Wrap to a runtime error to provide better visibility upstream
            raise RuntimeError(f"Failed to fetch profile '{self.username}': {exc}") from exc

        return PlatformCounts(
            platform=self.name,
            follower_count=profile.followers,
            following_count=profile.followees,
        )


def create_instagram_adapter(env: Mapping[str, str]) -> InstagramAdapter:
    """Create an Instagram adapter from env vars."""
    username = env.get("INSTAGRAM_USERNAME", "").strip()
    if not username:
        raise AdapterConfigError("Skipping instagram: missing INSTAGRAM_USERNAME in environment.")

    return InstagramAdapter(username=username)
