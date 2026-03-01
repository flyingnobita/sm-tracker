"""Live integration test for the Instagram adapter."""

from __future__ import annotations

import os

import pytest

from sm_tracker.platforms.instagram import InstagramAdapter


@pytest.mark.integration
def test_instagram_fetch_counts() -> None:
    account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "").strip()
    access_token = os.environ.get("LONG_LIVED_USER_TOKEN", "").strip()
    if not account_id or not access_token:
        pytest.skip("INSTAGRAM_ACCOUNT_ID and LONG_LIVED_USER_TOKEN not set")

    adapter = InstagramAdapter.from_env(dict(os.environ))
    counts = adapter.fetch_counts()

    assert counts.platform == "instagram"
    assert counts.follower_count is None or counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
