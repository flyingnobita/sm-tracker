"""Live integration test for the Farcaster adapter."""

from __future__ import annotations

import os

import pytest

from sm_tracker.platforms.farcaster import create_farcaster_adapter


@pytest.mark.integration
def test_farcaster_fetch_counts() -> None:
    api_key = os.environ.get("FARCASTER_API_KEY", "").strip()
    username = os.environ.get("FARCASTER_USERNAME", "").strip()
    if not api_key or not username:
        pytest.skip("FARCASTER_API_KEY and FARCASTER_USERNAME not set")

    adapter = create_farcaster_adapter(dict(os.environ))
    counts = adapter.fetch_counts()

    assert counts.platform == "farcaster"
    assert counts.follower_count is None or counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
