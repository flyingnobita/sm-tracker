"""Live integration test for the Facebook adapter."""

from __future__ import annotations

import os

import pytest

from sm_tracker.platforms.facebook import create_facebook_adapter


@pytest.mark.integration
def test_facebook_fetch_counts() -> None:
    page_access_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    if not page_access_token:
        pytest.skip("FACEBOOK_PAGE_ACCESS_TOKEN not set")

    adapter = create_facebook_adapter(dict(os.environ))
    counts = adapter.fetch_counts()

    assert counts.platform == "facebook"
    assert counts.follower_count is None or counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
