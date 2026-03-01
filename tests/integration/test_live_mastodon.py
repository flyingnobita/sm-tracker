"""Live integration test for the Mastodon adapter."""

from __future__ import annotations

import os

import pytest

from sm_tracker.platforms.mastodon import create_mastodon_adapter


@pytest.mark.integration
def test_mastodon_fetch_counts() -> None:
    access_token = os.environ.get("MASTODON_ACCESS_TOKEN", "").strip()
    instance = os.environ.get("MASTODON_INSTANCE", "").strip()
    if not access_token or not instance:
        pytest.skip("MASTODON_ACCESS_TOKEN and MASTODON_INSTANCE not set")

    adapter = create_mastodon_adapter(dict(os.environ))
    counts = adapter.fetch_counts()

    assert counts.platform == "mastodon"
    assert counts.follower_count is None or counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
