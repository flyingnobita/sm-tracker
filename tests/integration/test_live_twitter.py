"""Live integration test for the Twitter adapter."""

from __future__ import annotations

import os

import pytest

from sm_tracker.platforms.twitter import create_twitter_adapter


@pytest.mark.integration
def test_twitter_fetch_counts() -> None:
    consumer_key = os.environ.get("TWITTER_CONSUMER_KEY", "").strip()
    consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET", "").strip()
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "").strip()
    access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "").strip()
    handle = os.environ.get("TWITTER_HANDLE", "").strip()
    if not all([consumer_key, consumer_secret, access_token, access_token_secret, handle]):
        pytest.skip(
            "TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, "
            "TWITTER_ACCESS_TOKEN_SECRET, and TWITTER_HANDLE not all set"
        )

    adapter = create_twitter_adapter(dict(os.environ))
    counts = adapter.fetch_counts()

    assert counts.platform == "twitter"
    assert counts.follower_count is None or counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
