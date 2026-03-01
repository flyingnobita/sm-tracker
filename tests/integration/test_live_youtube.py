"""Live integration test for the YouTube adapter."""

from __future__ import annotations

import os

import pytest

from sm_tracker.platforms.youtube import YouTubeAdapter


@pytest.mark.integration
def test_youtube_fetch_counts() -> None:
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    has_target = bool(
        os.environ.get("YOUTUBE_HANDLE", "").strip()
        or os.environ.get("YOUTUBE_CHANNEL_ID", "").strip()
    )
    if not api_key or not has_target:
        pytest.skip("YOUTUBE_API_KEY and one of YOUTUBE_HANDLE/YOUTUBE_CHANNEL_ID not set")

    adapter = YouTubeAdapter.from_env(dict(os.environ))
    counts = adapter.fetch_counts()

    assert counts.platform == "youtube"
    assert counts.follower_count is None or counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
