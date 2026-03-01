"""Live integration test for the Bluesky adapter."""

from __future__ import annotations

import os

import pytest

from sm_tracker.platforms.bluesky import create_bluesky_adapter


@pytest.mark.integration
def test_bluesky_fetch_counts() -> None:
    handle = os.environ.get("BLUESKY_HANDLE", "").strip()
    if not handle:
        pytest.skip("BLUESKY_HANDLE not set")

    adapter = create_bluesky_adapter(dict(os.environ))
    counts = adapter.fetch_counts()

    assert counts.platform == "bluesky"
    assert counts.follower_count is None or counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
