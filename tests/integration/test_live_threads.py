"""Live integration test for the Threads adapter."""

from __future__ import annotations

import os

import pytest

from sm_tracker.platforms.threads import ThreadsAdapter


@pytest.mark.integration
def test_threads_fetch_counts() -> None:
    access_token = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
    user_id = os.environ.get("THREADS_USER_ID", "").strip()
    if not access_token or not user_id:
        pytest.skip("THREADS_ACCESS_TOKEN and THREADS_USER_ID not set")

    adapter = ThreadsAdapter.from_env(dict(os.environ))
    counts = adapter.fetch_counts()

    assert counts.platform == "threads"
    assert counts.follower_count is None or counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
